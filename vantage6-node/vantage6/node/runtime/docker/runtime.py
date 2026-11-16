import io
import logging
import os
import posixpath
import tarfile
import time
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import docker
from docker.auth import resolve_repository_name
from docker.errors import APIError, DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
from docker.types import DeviceRequest
from docker.utils import parse_repository_tag

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.common.globals import DEFAULT_ALPINE_IMAGE, DEFAULT_DOCKER_REGISTRY

from vantage6.cli.context.node import NodeContext

from vantage6.node.container.exceptions import PermanentAlgorithmStartFail
from vantage6.node.globals import (
    ISOLATION_PROBE_CANDIDATES,
    ISOLATION_PROBE_IMAGE,
    ISOLATION_PROBE_TIMEOUT_SECONDS,
    TASK_FILES_ROOT,
)
from vantage6.node.runtime.base import (
    ContainerRuntime,
    MountSpec,
    PullPolicy,
    RegistryCredentials,
    RunInfo,
    RunMetadata,
    RunSpec,
    StorageKind,
)
from vantage6.node.runtime.docker.egress import (
    SQUID_PORT,
    HttpWhitelist,
    parse_whitelist,
    squid_config,
)
from vantage6.node.runtime.docker.engine import DOCKER, EngineSettings
from vantage6.node.runtime.docker.status import container_state
from vantage6.node.runtime.probe import probe_args

DEFAULT_SQUID_IMAGE = f"{DEFAULT_DOCKER_REGISTRY}/infrastructure/squid:latest"

LABEL_NODE = "vantage6.node_id"
LABEL_TYPE = "vantage6.type"
LABEL_RUN_NAME = "vantage6.run_name"
LABEL_STEP = "vantage6.step"
METADATA_LABEL_PREFIX = "vantage6.run."

TYPE_ALGORITHM = "algorithm"
TYPE_SQUID = "squid"
TYPE_PROBE = "probe"

SQUID_ALIAS = "squid"
TEST_FILE_NAME = ".v6-runtime-check"


class DockerRuntime(ContainerRuntime):
    """
    Runs algorithms as sibling containers of the node container, through the
    container engine API that is mounted in the node container.

    Algorithm containers only see the files of their own run and session. Steps
    without network access get no network at all. Central compute runs share an
    internal network with the node, so that they can reach the node proxy and
    nothing else. Steps with an HTTP(S) whitelist reach the outside through a Squid
    proxy on their own internal network.
    """

    name = "docker"
    engine: EngineSettings = DOCKER

    def __init__(
        self, ctx: NodeContext, client: docker.DockerClient | None = None
    ) -> None:
        super().__init__(ctx)
        self.log = logging.getLogger(logger_name(__name__))
        cfg = ctx.config.get("docker") or {}

        self.node_container = os.environ.get("V6_NODE_CONTAINER_NAME") or cfg.get(
            "node_container"
        )
        if not self.node_container:
            raise ValueError(
                "The node does not know the name of its own container. Please start "
                "the node with `v6 node start`."
            )
        self.client = client or docker.DockerClient(
            base_url=cfg.get("host") or self.engine.base_url
        )

        # Paths on the container host of what is mounted in the node container, as
        # the engine reports them. These are valid for sibling containers, also where
        # the engine translates paths (e.g. Docker Desktop).
        self.own_mounts = self._own_mounts()
        self.task_host_path = self.own_mounts.get(TASK_FILES_ROOT) or (
            cfg.get("task_storage") or {}
        ).get("host_path")
        if not self.task_host_path:
            raise ValueError(
                f"Cannot determine where {TASK_FILES_ROOT} of the node container is "
                "stored on the host. Please start the node with `v6 node start`."
            )
        self.node_id = ctx.identifier
        self.prefix = cfg.get("resource_prefix") or self.node_container
        self.egress_network = cfg.get("egress_network")
        self.squid_image = cfg.get("squid_image") or DEFAULT_SQUID_IMAGE
        self.preflight_image = cfg.get("preflight_image") or DEFAULT_ALPINE_IMAGE
        self.probe_image = (ctx.config.get("network_isolation") or {}).get(
            "probe_image"
        ) or ISOLATION_PROBE_IMAGE
        self.container_settings = self._container_settings(
            cfg.get("algorithm_containers") or {}
        )
        self.whitelists = parse_whitelist(ctx.config.get("whitelist"))
        if self.whitelists and not self.egress_network:
            raise ValueError(
                "A whitelist is configured, but the node configuration has no "
                "'docker.egress_network' for the proxy to reach the outside."
            )

    def _own_mounts(self) -> dict[str, str]:
        try:
            node = self.client.containers.get(self.node_container)
        except DockerException as exc:
            self.log.warning("Cannot inspect the node container: %s", exc)
            return {}
        return {
            mount["Destination"]: mount["Source"]
            for mount in node.attrs.get("Mounts") or []
            if mount.get("Type") == "bind"
        }

    # ------------------------------------------------------------------ settings
    @staticmethod
    def _container_settings(cfg: dict) -> dict:
        """Translate ``docker.algorithm_containers`` to container create options."""
        if cfg.get("privileged"):
            raise ValueError("Algorithm containers cannot be privileged.")
        settings = {
            "security_opt": cfg.get("security_opt", ["no-new-privileges:true"]),
        }
        if cfg.get("cpus"):
            settings["nano_cpus"] = int(float(cfg["cpus"]) * 1e9)
        if cfg.get("memory"):
            settings["mem_limit"] = cfg["memory"]
        if cfg.get("memory_reservation"):
            settings["mem_reservation"] = cfg["memory_reservation"]
        if cfg.get("pids_limit"):
            settings["pids_limit"] = int(cfg["pids_limit"])
        if cfg.get("gpus"):
            count = -1 if cfg["gpus"] == "all" else int(cfg["gpus"])
            settings["device_requests"] = [
                DeviceRequest(count=count, capabilities=[["gpu"]])
            ]
        for key in ("runtime", "user", "read_only", "cap_drop", "shm_size"):
            if cfg.get(key):
                settings[key] = cfg[key]
        return settings

    def _network_name(self, step: AlgorithmStepType) -> str:
        return f"{self.prefix}-{step.value.replace('_', '-')}"

    def _squid_name(self, step: AlgorithmStepType) -> str:
        return f"{self.prefix}-squid-{step.value.replace('_', '-')}"

    def _networked_steps(self) -> set[AlgorithmStepType]:
        return {AlgorithmStepType.CENTRAL_COMPUTE, *self.whitelists}

    def _container_name(self, name: str) -> str:
        # Run ids are only unique per HQ, so include the node
        return f"{name}-{self.node_id[:8]}"

    def _labels(self, type_: str, **extra: str) -> dict[str, str]:
        return {LABEL_NODE: self.node_id, LABEL_TYPE: type_, **extra}

    def _filters(self, type_: str, **labels: str) -> dict:
        return {
            "label": [f"{LABEL_NODE}={self.node_id}", f"{LABEL_TYPE}={type_}"]
            + [f"{k}={v}" for k, v in labels.items()]
        }

    # ----------------------------------------------------------- node lifecycle
    def describe(self) -> str:
        return f"{self.engine.name} (node container '{self.node_container}')"

    def prepare(self) -> None:
        self._remove_containers(self._filters(TYPE_PROBE))
        # Containers that were created but never started by a previous node process
        for container in self.client.containers.list(
            all=True, filters={**self._filters(TYPE_ALGORITHM), "status": "created"}
        ):
            self.log.info(
                "Removing algorithm container %s that never started", container.name
            )
            container.remove(force=True)

        for step in self._networked_steps():
            self._ensure_network(self._network_name(step))
        self._connect_node(self._network_name(AlgorithmStepType.CENTRAL_COMPUTE))

        self._remove_containers(self._filters(TYPE_SQUID))
        for step, whitelist in self.whitelists.items():
            self._start_squid(step, whitelist)

    def _ensure_network(self, name: str):
        networks = self.client.networks.list(names=[name])
        network = next((n for n in networks if n.name == name), None)
        if network is not None:
            if not network.attrs.get("Internal"):
                raise RuntimeError(
                    f"Network '{name}' exists but is not internal. Remove it, so that "
                    "the node can create it as an internal network."
                )
            return network
        self.log.info("Creating internal network %s", name)
        return self.client.networks.create(
            name,
            driver="bridge",
            internal=True,
            labels=self._labels("network"),
        )

    def _connect_node(self, network_name: str) -> None:
        network = self.client.networks.get(network_name)
        node = self.client.containers.get(self.node_container)
        if network_name not in node.attrs["NetworkSettings"]["Networks"]:
            self.log.info("Connecting node container to network %s", network_name)
            network.connect(node)

    def _start_squid(self, step: AlgorithmStepType, whitelist: HttpWhitelist) -> None:
        name = self._squid_name(step)
        self._pull_if_missing(self.squid_image)
        self.log.info(
            "Starting proxy %s for %s: domains %s, IPs %s, ports %s",
            name,
            step.value,
            list(whitelist.domains),
            list(whitelist.ips),
            list(whitelist.ports),
        )
        container = self.client.containers.create(
            self.squid_image,
            name=name,
            labels=self._labels(TYPE_SQUID, **{LABEL_STEP: step.value}),
            network=self.egress_network,
            security_opt=["no-new-privileges:true"],
        )
        container.put_archive("/etc/squid", _tar("squid.conf", squid_config(whitelist)))
        self.client.networks.get(self._network_name(step)).connect(
            container, aliases=[SQUID_ALIAS]
        )
        container.start()

    def _remove_containers(self, filters: dict) -> None:
        for container in self.client.containers.list(all=True, filters=filters):
            try:
                container.remove(force=True)
            except NotFound:
                pass

    def cleanup(self) -> None:
        self._remove_containers(self._filters(TYPE_SQUID))
        self._remove_containers(self._filters(TYPE_PROBE))
        for step in self._networked_steps():
            try:
                network = self.client.networks.get(self._network_name(step))
                network.reload()
                for container in network.containers:
                    network.disconnect(container, force=True)
                network.remove()
            except (NotFound, APIError) as exc:
                self.log.warning("Could not remove network: %s", exc)

    def preflight(self) -> tuple[bool, str]:
        """
        Check that the engine is reachable, and that a container started by the
        node sees the files the node writes to its task storage.
        """
        try:
            self.client.ping()
        except DockerException as exc:
            return False, f"Cannot reach the {self.engine.name} API: {exc}"

        marker = f"{TEST_FILE_NAME}-{uuid.uuid4().hex[:8]}"
        marker_path = Path(TASK_FILES_ROOT) / marker
        marker_path.write_text("ok")
        try:
            self._pull_if_missing(self.preflight_image)
            exit_code, output = self._run_to_completion(
                self.preflight_image,
                ["cat", f"/check/{marker}"],
                mounts=[self.engine.bind(self.task_host_path, "/check", True)],
                network_mode="none",
            )
        except DockerException as exc:
            return False, f"Failed to start a test container: {exc}"
        finally:
            marker_path.unlink(missing_ok=True)

        if exit_code != 0 or output.strip() != "ok":
            return False, (
                f"A test container could not read the node's task files from "
                f"'{self.task_host_path}'. Check that this host path is the one "
                f"mounted at {TASK_FILES_ROOT} in the node container."
            )
        return True, f"Algorithm containers can be started with {self.describe()}."

    def verify_isolation(self) -> tuple[bool, str]:
        step = AlgorithmStepType.CENTRAL_COMPUTE
        network_name = self._network_name(step)
        try:
            network = self.client.networks.get(network_name)
        except NotFound:
            return False, f"Network '{network_name}' does not exist."
        if not network.attrs.get("Internal"):
            return False, f"Network '{network_name}' is not an internal network."

        try:
            self._pull_if_missing(self.probe_image)
        except DockerException as exc:
            return False, f"Could not pull isolation probe image: {exc}"

        reached = []
        for url in ISOLATION_PROBE_CANDIDATES:
            try:
                exit_code, _ = self._run_to_completion(
                    self.probe_image,
                    ["curl", *probe_args(url)],
                    network=network_name,
                    environment=self._proxy_env(step),
                    timeout=ISOLATION_PROBE_TIMEOUT_SECONDS,
                    **self.container_settings,
                )
            except TimeoutError as exc:
                return False, str(exc)
            except DockerException as exc:
                return False, f"Failed to run isolation probe: {exc}"
            if exit_code == 0:
                reached.append(url)

        if reached:
            return False, (
                "Algorithm containers can reach the public internet (reached: "
                f"{', '.join(reached)}). Check the whitelist of central_compute."
            )
        return True, "Algorithm network isolation verified."

    def _run_to_completion(
        self,
        image: str,
        command: list[str],
        timeout: int = ISOLATION_PROBE_TIMEOUT_SECONDS,
        **kwargs,
    ) -> tuple[int, str]:
        container = self.client.containers.create(
            image,
            command=command,
            name=f"v6-probe-{uuid.uuid4().hex[:8]}",
            labels=self._labels(TYPE_PROBE),
            **kwargs,
        )
        try:
            container.start()
            try:
                result = container.wait(timeout=timeout)
            except Exception as exc:  # noqa: BLE001
                raise TimeoutError(
                    f"Probe container did not complete within {timeout}s"
                ) from exc
            output = container.logs(stdout=True, stderr=False).decode(errors="replace")
            return result.get("StatusCode", 1), output
        finally:
            container.remove(force=True)

    # ------------------------------------------------------------------- images
    def _pull_if_missing(self, image: str) -> None:
        try:
            self.client.images.get(image)
        except ImageNotFound:
            self._pull(image, [])

    def _pull(self, image: str, registries: list[RegistryCredentials]) -> None:
        repository, tag = parse_repository_tag(image)
        auth_config = _auth_config(repository, registries)
        self.client.images.pull(repository, tag=tag, auth_config=auth_config)

    # --------------------------------------------------------------------- runs
    def _mount(self, mount: MountSpec):
        if mount.storage.kind == StorageKind.TASK:
            sub_path = posixpath.normpath(mount.sub_path)
            if sub_path.startswith(("/", "..")) or sub_path == ".":
                raise PermanentAlgorithmStartFail(
                    f"Refusing to mount '{mount.sub_path}': it is not a file or "
                    "folder inside the task storage."
                )
            source = posixpath.join(self.task_host_path, sub_path)
        elif mount.storage.kind == StorageKind.HOST_PATH:
            # A database is mounted at the same path in the node container
            source = self.own_mounts.get(mount.target) or mount.storage.name
            if mount.sub_path:
                source = posixpath.join(source, mount.sub_path)
        else:
            raise PermanentAlgorithmStartFail(
                f"Cannot mount volume claim '{mount.storage.name}' with "
                f"{self.engine.name}. Configure a host path for this database."
            )
        return self.engine.bind(source, mount.target, mount.read_only)

    def _proxy_env(self, step: AlgorithmStepType) -> dict[str, str]:
        if step not in self.whitelists:
            return {}
        proxy = f"http://{SQUID_ALIAS}:{SQUID_PORT}"
        no_proxy = f"{self.node_container},localhost,127.0.0.1"
        return {
            "HTTP_PROXY": proxy,
            "HTTPS_PROXY": proxy,
            "http_proxy": proxy,
            "https_proxy": proxy,
            "NO_PROXY": no_proxy,
            "no_proxy": no_proxy,
        }

    def _network_kwargs(self, step: AlgorithmStepType) -> dict:
        if step in self._networked_steps():
            return {"network": self._network_name(step)}
        return {"network_mode": "none"}

    def start_run(
        self, spec: RunSpec, on_status_change: Callable[[RunStatus], None]
    ) -> RunStatus:
        try:
            if spec.pull_policy == PullPolicy.ALWAYS:
                on_status_change(RunStatus.PULLING_IMAGE)
                self._pull(spec.image, spec.registries)
            else:
                try:
                    self.client.images.get(spec.image)
                except ImageNotFound:
                    on_status_change(RunStatus.PULLING_IMAGE)
                    self._pull(spec.image, spec.registries)
        except (NotFound, APIError) as exc:
            self.log.error("Could not pull image %s: %s", spec.image, exc)
            return RunStatus.NO_DOCKER_IMAGE

        mounts = [self._mount(m) for m in spec.mounts]
        on_status_change(RunStatus.INITIALIZING)
        container = self.client.containers.create(
            spec.image,
            name=self._container_name(spec.name),
            labels=self._labels(
                TYPE_ALGORITHM,
                **{LABEL_RUN_NAME: spec.name, LABEL_STEP: spec.step.value},
                **{
                    f"{METADATA_LABEL_PREFIX}{k}": v
                    for k, v in spec.metadata.to_dict().items()
                },
            ),
            environment={
                **spec.env,
                **spec.secret_env,
                **self._proxy_env(spec.step),
            },
            mounts=mounts,
            tty=True,
            **self._network_kwargs(spec.step),
            **self.container_settings,
        )
        container.start()
        return RunStatus.ACTIVE

    def _algorithm_containers(self, **labels: str) -> list[Container]:
        return self.client.containers.list(
            all=True, filters=self._filters(TYPE_ALGORITHM, **labels)
        )

    def _run_info(self, container: Container) -> RunInfo:
        labels = container.labels
        metadata = {
            key.removeprefix(METADATA_LABEL_PREFIX): value
            for key, value in labels.items()
            if key.startswith(METADATA_LABEL_PREFIX)
        }
        state, exit_code, reason = container_state(container.attrs)
        return RunInfo(
            name=labels[LABEL_RUN_NAME],
            state=state,
            metadata=RunMetadata.from_dict(metadata),
            exit_code=exit_code,
            reason=reason,
        )

    def list_runs(self) -> list[RunInfo]:
        runs = []
        for container in self._algorithm_containers():
            try:
                runs.append(self._run_info(container))
            except (KeyError, ValueError) as exc:
                self.log.warning(
                    "Ignoring container %s with incomplete labels: %s",
                    container.name,
                    exc,
                )
        return runs

    def run_exists(self, name: str) -> bool:
        return bool(self._algorithm_containers(**{LABEL_RUN_NAME: name}))

    def _get(self, name: str) -> Container | None:
        containers = self._algorithm_containers(**{LABEL_RUN_NAME: name})
        return containers[0] if containers else None

    def logs(self, name: str) -> str:
        container = self._get(name)
        if container is None:
            return ""
        return container.logs(stdout=True, stderr=True).decode(errors="replace")

    def stream_logs(self, name: str) -> Iterator[str]:
        container = self._get(name)
        if container is None:
            self.log.error("No container found for %s", name)
            return
        buffer = ""
        for chunk in container.logs(stream=True, follow=True):
            buffer += chunk.decode(errors="replace")
            *lines, buffer = buffer.split("\n")
            yield from (line.rstrip("\r") for line in lines)
        if buffer:
            yield buffer

    def remove_run(self, name: str, run_id: int) -> None:
        for container in self._algorithm_containers(**{LABEL_RUN_NAME: name}):
            self.log.info("Removing container %s (run_id = %s)", container.name, run_id)
            try:
                container.remove(force=True)
            except NotFound:
                pass

    def host_reachable_url(self, url: str) -> str:
        parts = urlsplit(url)
        if parts.hostname not in ("localhost", "127.0.0.1"):
            return url
        netloc = self.engine.host_gateway_name
        if parts.port:
            netloc += f":{parts.port}"
        return urlunsplit(parts._replace(netloc=netloc))


def _auth_config(repository: str, registries: list[RegistryCredentials]) -> dict | None:
    registry, _ = resolve_repository_name(repository)
    for credentials in registries:
        configured = credentials.registry.split("://", 1)[-1].rstrip("/")
        if configured in (registry, f"index.{registry}"):
            return {"username": credentials.username, "password": credentials.password}
    return None


def _tar(name: str, content: str) -> bytes:
    data = content.encode()
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode="w") as archive:
        info = tarfile.TarInfo(name)
        info.size = len(data)
        info.mode = 0o644
        info.mtime = int(time.time())
        archive.addfile(info, io.BytesIO(data))
    return stream.getvalue()
