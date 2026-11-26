import os
import platform
import sys
from pathlib import Path
from urllib.parse import urlsplit

import docker
import yaml
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container
from docker.types import Mount

from vantage6.common import error, info, warning
from vantage6.common.kubernetes.utils import running_on_windows

from vantage6.cli.context.node import NodeContext
from vantage6.cli.deployment.base import NodeDeployment
from vantage6.cli.deployment.docker_config import (
    DATA_DIR,
    DOCKER_SOCKET,
    LOG_DIR,
    NODE_CONFIG_PATH,
    PRIVATE_KEY_PATH,
    TASK_FILES_ROOT,
    database_mount_path,
    database_read_only,
    egress_network,
    file_databases,
    node_environment,
    runtime_config,
)
from vantage6.cli.node.common.private_key import (
    delete_private_key_secret,
    private_key_file,
    read_private_key_secret,
    write_private_key_secret,
)

LABEL_NODE = "vantage6.node_id"
LABEL_TYPE = "vantage6.type"
LABEL_CONFIG = "vantage6.config"
TYPE_NODE = "node"


def _candidate_hosts() -> list[str]:
    if os.environ.get("DOCKER_HOST"):
        return [os.environ["DOCKER_HOST"]]
    if running_on_windows():
        return ["npipe:////./pipe/docker_engine"]
    candidates = ["unix:///var/run/docker.sock"]
    if xdg := os.environ.get("XDG_RUNTIME_DIR"):
        candidates.append(f"unix://{xdg}/docker.sock")
    candidates.append(f"unix://{Path.home()}/.docker/run/docker.sock")
    return candidates


def docker_client(host: str | None = None) -> docker.DockerClient:
    """Connect to the Docker engine, trying the usual socket locations."""
    errors = []
    for url in [host] if host else _candidate_hosts():
        try:
            client = docker.DockerClient(base_url=url)
            client.ping()
            return client
        except DockerException as exc:
            errors.append(f"{url}: {exc}")
    raise DockerException(
        "Cannot connect to Docker. Is it running? Set 'node.docker.host' in the node "
        "configuration or DOCKER_HOST to point at it. Tried: " + "; ".join(errors)
    )


class DockerNodeDeployment(NodeDeployment):
    """Runs the node as a container that starts algorithm containers next to it."""

    def __init__(
        self, ctx: NodeContext, client: docker.DockerClient | None = None
    ) -> None:
        super().__init__(ctx)
        self.node = ctx.config["node"]
        self.docker_cfg = self.node.get("docker") or {}
        self._client = client

    @property
    def client(self) -> docker.DockerClient:
        if self._client is None:
            self._client = docker_client(self.docker_cfg.get("host"))
        return self._client

    def describe_target(self) -> str:
        return f"Docker ({self.client.api.base_url})"

    # ------------------------------------------------------------------ paths
    @property
    def task_dir(self) -> Path:
        return Path(self.ctx.data_dir) / "tasks"

    @property
    def runtime_dir(self) -> Path:
        return Path(self.ctx.data_dir) / "runtime"

    @property
    def private_key_file(self) -> Path:
        return private_key_file(self.ctx)

    def _engine_info(self) -> dict:
        return self.client.info()

    def _is_desktop(self, engine_info: dict) -> bool:
        return "Docker Desktop" in (engine_info.get("OperatingSystem") or "")

    def _socket_path(self, engine_info: dict) -> str:
        """Path of the engine socket on the engine's host, to mount in the node."""
        if path := self.docker_cfg.get("socketPath"):
            return path
        base_url = urlsplit(self.client.api.base_url)
        if not self._is_desktop(engine_info) and base_url.scheme in (
            "unix",
            "http+unix",
        ):
            path = base_url.path or DOCKER_SOCKET
            if path.startswith("/"):
                return path
        return DOCKER_SOCKET

    def _user_settings(self, engine_info: dict, socket_path: str) -> dict:
        """
        On a native Linux engine, run as the current user so that the files the node
        writes in the user's folders stay theirs, with access to the socket.
        Rootless engines and Docker Desktop map ownership themselves.
        """
        rootless = any(
            "rootless" in option for option in engine_info.get("SecurityOptions") or []
        )
        if (
            platform.system() != "Linux"
            or self._is_desktop(engine_info)
            or rootless
            or not hasattr(os, "getuid")
        ):
            return {}
        settings = {"user": f"{os.getuid()}:{os.getgid()}"}
        try:
            settings["group_add"] = [str(os.stat(socket_path).st_gid)]
        except OSError:
            warning(f"Cannot read the group of {socket_path}; the node may lack access")
        return settings

    # ------------------------------------------------------------- lifecycle
    def _get_container(self) -> Container | None:
        try:
            return self.client.containers.get(self.name)
        except NotFound:
            return None

    def is_running(self) -> bool:
        container = self._get_container()
        return container is not None and container.status == "running"

    def _check_private_key(self) -> None:
        if not (self.node.get("encryption") or {}).get("enabled"):
            return
        if not self.private_key_file.exists():
            error(
                "Encryption is enabled, but the node has no private key at "
                f"{self.private_key_file}."
            )
            info("Create it with 'v6 node create-private-key'.")
            sys.exit(1)

    def _ensure_egress_network(self) -> str:
        name = egress_network(self.name)
        if not self.client.networks.list(names=[name]):
            self.client.networks.create(
                name,
                driver="bridge",
                labels={LABEL_NODE: self.ctx.identifier, LABEL_TYPE: "network"},
            )
        return name

    def _pull_node_image(self, image: str) -> None:
        policy = self.node.get("imagePullPolicy", "Always")
        if policy == "Never":
            return
        if policy == "IfNotPresent":
            try:
                self.client.images.get(image)
                return
            except ImageNotFound:
                pass
        info(f"Pulling node image {image}")
        try:
            self.client.images.pull(image)
        except DockerException as exc:
            try:
                self.client.images.get(image)
                warning(f"Could not pull {image}, using the local image: {exc}")
            except ImageNotFound:
                error(f"Could not pull node image {image}: {exc}")
                sys.exit(1)

    def _write_runtime_config(self) -> Path:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        path = self.runtime_dir / "config.yml"
        config = runtime_config(self.node, self.name, str(self.task_dir.resolve()))
        # Contains registry passwords, like the Kubernetes ConfigMap does
        path.touch(mode=0o600, exist_ok=True)
        path.chmod(0o600)
        path.write_text(yaml.safe_dump(config, sort_keys=False))
        return path

    def _mounts(self, config_path: Path, socket_path: str) -> list[Mount]:
        mounts = [
            Mount(DOCKER_SOCKET, socket_path, type="bind"),
            Mount(NODE_CONFIG_PATH, str(config_path), type="bind", read_only=True),
            Mount(TASK_FILES_ROOT, str(self.task_dir.resolve()), type="bind"),
            Mount(LOG_DIR, str(Path(self.ctx.log_dir).resolve()), type="bind"),
            Mount(
                DATA_DIR, str((Path(self.ctx.data_dir) / "node").resolve()), type="bind"
            ),
        ]
        if (self.node.get("encryption") or {}).get("enabled"):
            mounts.append(
                Mount(
                    PRIVATE_KEY_PATH,
                    str(self.private_key_file.resolve()),
                    type="bind",
                    read_only=True,
                )
            )
        for db in file_databases(self.node):
            source = Path(db["path"]).expanduser().resolve()
            if not source.exists():
                error(f"Database '{db['name']}' not found at {source}")
                sys.exit(1)
            mounts.append(
                Mount(
                    database_mount_path(db),
                    str(source),
                    type="bind",
                    read_only=database_read_only(db),
                )
            )
        return mounts

    def start(self, image: str) -> None:
        existing = self._get_container()
        if existing is not None:
            if existing.status == "running":
                error(f"Node {self.name} is already running.")
                sys.exit(1)
            existing.remove(force=True)

        self._check_private_key()
        for folder in (
            self.task_dir,
            Path(self.ctx.log_dir),
            Path(self.ctx.data_dir) / "node",
        ):
            folder.mkdir(parents=True, exist_ok=True)

        engine_info = self._engine_info()
        socket_path = self._socket_path(engine_info)
        self._pull_node_image(image)
        network = self._ensure_egress_network()
        config_path = self._write_runtime_config()

        self.client.containers.run(
            image,
            command=["vnode-local", "start", "-c", NODE_CONFIG_PATH],
            name=self.name,
            detach=True,
            labels={
                LABEL_NODE: self.ctx.identifier,
                LABEL_TYPE: TYPE_NODE,
                LABEL_CONFIG: self.ctx.name,
            },
            environment=node_environment(self.node, self.name),
            mounts=self._mounts(config_path, socket_path),
            network=network,
            restart_policy={"Name": "unless-stopped"},
            extra_hosts={"host.docker.internal": "host-gateway"},
            **self._user_settings(engine_info, socket_path),
        )
        info(f"Node {self.name} started with {self.describe_target()}.")

    def stop(self) -> None:
        container = self._get_container()
        if container is not None:
            info(f"Stopping node container {self.name}")
            container.stop(timeout=30)
            container.remove(force=True)
        self.cleanup_runs()
        info(f"Node {self.name} stopped successfully.")

    def cleanup_runs(self) -> None:
        """Remove the algorithm containers, helpers and networks of this node."""
        label = f"{LABEL_NODE}={self.ctx.identifier}"
        for container in self.client.containers.list(
            all=True, filters={"label": [label]}
        ):
            info(f"Removing container {container.name}")
            container.remove(force=True)
        for network in self.client.networks.list(filters={"label": [label]}):
            try:
                network.remove()
            except DockerException as exc:
                warning(f"Could not remove network {network.name}: {exc}")

    def attach_logs(self) -> None:
        container = self._get_container()
        if container is None:
            error(f"Node {self.name} is not running.")
            return
        try:
            for chunk in container.logs(stream=True, follow=True, tail=100):
                sys.stdout.write(chunk.decode(errors="replace"))
                sys.stdout.flush()
        except KeyboardInterrupt:
            info("Detached from node logs.")

    def exec(self, command: list[str]) -> str:
        container = self._get_container()
        if container is None:
            error(f"Node {self.name} is not running.")
            sys.exit(1)
        return container.exec_run(command).output.decode(errors="replace")

    # ------------------------------------------------------------ private key
    def read_private_key(self) -> bytes | None:
        return read_private_key_secret(self.ctx, None)

    def write_private_key(self, pem: bytes) -> None:
        write_private_key_secret(self.ctx, None, pem)

    def delete_private_key(self) -> bool:
        return delete_private_key_secret(self.ctx, None)


def running_docker_nodes(client: docker.DockerClient | None = None) -> list[str]:
    """Names of the node containers that run on the local Docker engine."""
    try:
        client = client or docker_client()
    except DockerException:
        return []
    return [
        container.name
        for container in client.containers.list(
            filters={"label": [f"{LABEL_TYPE}={TYPE_NODE}"]}
        )
    ]


def running_docker_node_contexts(system_folders: bool) -> list[NodeContext]:
    """Contexts of the running Docker nodes of the user or system folders."""
    from vantage6.common.globals import InstanceType

    from vantage6.cli.common.utils import get_config_name_from_helm_release_name
    from vantage6.cli.context import get_context
    from vantage6.cli.deployment import DOCKER, node_config_runtimes

    if DOCKER not in node_config_runtimes(system_folders):
        return []
    scope = "system" if system_folders else "user"
    contexts = []
    for container_name in running_docker_nodes():
        if not container_name.endswith(f"-{scope}-node"):
            continue
        config_name = get_config_name_from_helm_release_name(container_name)
        for is_sandbox in (False, True):
            if NodeContext.config_exists(config_name, system_folders, is_sandbox):
                contexts.append(
                    get_context(
                        InstanceType.NODE,
                        config_name,
                        system_folders,
                        is_sandbox=is_sandbox,
                    )
                )
                break
    return contexts
