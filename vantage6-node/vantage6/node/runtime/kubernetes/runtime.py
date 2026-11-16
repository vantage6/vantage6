import base64
import json
import logging
import os
import posixpath
import uuid
from collections.abc import Callable, Iterator
from pathlib import Path

from kubernetes import client as k8s_client, config, watch
from kubernetes.client.rest import ApiException

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.common.globals import DEFAULT_ALPINE_IMAGE

from vantage6.cli.context.node import NodeContext
from vantage6.cli.node.common.task_cleanup import delete_run_related_pods
from vantage6.cli.utils_kubernetes import replace_localhost_for_k8s

from vantage6.node.container.exceptions import PermanentAlgorithmStartFail
from vantage6.node.globals import (
    ISOLATION_PROBE_IMAGE,
    K8S_EVENT_STREAM_LOOP_TIMEOUT,
    SERVICE_ACCOUNT_NAMESPACE_FILE,
    TASK_START_RETRIES,
)
from vantage6.node.runtime.base import (
    ContainerRuntime,
    MountSpec,
    PullPolicy,
    RegistryCredentials,
    RunInfo,
    RunMetadata,
    RunSpec,
    RunState,
    StorageKind,
)
from vantage6.node.runtime.kubernetes.network_isolation import (
    validate_algorithm_isolation,
)
from vantage6.node.runtime.kubernetes.status import compute_run_pod_status

PULL_POLICIES = {
    PullPolicy.ALWAYS: "Always",
    PullPolicy.IF_NOT_PRESENT: "IfNotPresent",
}


def algorithm_pod_labels(release_name: str | None) -> dict[str, str]:
    """
    Labels of every pod the node starts for algorithm runs. The node Helm chart
    selects pods by these labels in its network policies.
    """
    labels = {"v6-pod-type": "algorithm"}
    if release_name:
        labels["v6-node-release"] = release_name
    return labels


def own_namespace() -> str:
    """Namespace of the pod this code runs in."""
    return Path(SERVICE_ACCOUNT_NAMESPACE_FILE).read_text().strip()


def join_sub_path(*parts: str | Path) -> str:
    """Join path parts into a relative ``subPath``, skipping empty parts."""
    return posixpath.join(*[str(p).strip("/") for p in parts if str(p).strip("/")])


class KubernetesRuntime(ContainerRuntime):
    """Runs algorithms as Jobs in the namespace of the node pod."""

    name = "kubernetes"

    def __init__(self, ctx: NodeContext) -> None:
        super().__init__(ctx)
        self.log = logging.getLogger(logger_name(__name__))

        # When a pod runs in Kubernetes with a ServiceAccount, Kubernetes automatically
        # mounts the service account credentials at
        # /var/run/secrets/kubernetes.io/serviceaccount/.
        try:
            config.load_incluster_config()
        except Exception:
            self.log.exception("Error loading Kubernetes configuration")
            raise

        # The claim that the node pod mounts at TASK_FILES_ROOT. Algorithm pods mount
        # only the files of their own run from it.
        task_storage = ctx.config.get("task_storage") or {}
        self.task_claim_name = task_storage.get("claim_name")
        if not self.task_claim_name:
            raise ValueError(
                "The node configuration has no 'task_storage.claim_name'. Please "
                "restart the node with a version of the node Helm chart that matches "
                "this node."
            )
        self.task_claim_sub_path = task_storage.get("sub_path") or ""
        self.colocate_with_node = bool(task_storage.get("colocate_with_node", False))
        self.node_pod_labels = ctx.config.get("node_pod_labels") or {}
        if self.colocate_with_node and not self.node_pod_labels:
            raise ValueError(
                "'task_storage.colocate_with_node' requires 'node_pod_labels' in the "
                "node configuration."
            )
        self.algorithm_pod_config = ctx.config.get("algorithm_pods") or {}
        self.algorithm_pod_labels = algorithm_pod_labels(ctx.config.get("release_name"))

        self.batch_api = k8s_client.BatchV1Api()
        self.core_api = k8s_client.CoreV1Api()
        # Algorithm pods run in the node's own namespace, as they share its claims
        self.task_namespace = ctx.config.get("task_namespace") or own_namespace()

        # labels to identify the task jobs of this node
        self.task_job_labels = {"node_id": ctx.identifier}
        self.task_job_label_selector = ",".join(
            [f"{k}={v}" for k, v in self.task_job_labels.items()]
        )

    def describe(self) -> str:
        return f"Kubernetes namespace '{self.task_namespace}'"

    def preflight(self) -> tuple[bool, str]:
        """Check that a test pod, configured like an algorithm pod, is accepted."""
        test_pod_name = "v6-test-pod-" + str(uuid.uuid4())
        try:
            self.core_api.create_namespaced_pod(
                namespace=self.task_namespace,
                body=k8s_client.V1Pod(
                    metadata=k8s_client.V1ObjectMeta(
                        name=test_pod_name, labels=self.algorithm_pod_labels
                    ),
                    spec=self.algorithm_pod_spec(
                        containers=[
                            self.algorithm_container(
                                name="test-container",
                                image=DEFAULT_ALPINE_IMAGE,
                                command=["true"],
                            )
                        ]
                    ),
                ),
            )
        except ApiException as exc:
            return False, (
                f"Failed to create test pod in namespace '{self.task_namespace}': "
                f"{exc}. Please check that the node's service account may create "
                "pods, jobs and secrets there."
            )
        self.core_api.delete_namespaced_pod(test_pod_name, self.task_namespace)
        return True, f"Algorithm pods can be created in {self.describe()}."

    def algorithm_container(self, **kwargs) -> k8s_client.V1Container:
        """Container with the resources and security context of algorithm pods."""
        return k8s_client.V1Container(
            resources=self.algorithm_pod_config.get("resources") or None,
            security_context=self.algorithm_pod_config.get("security_context") or None,
            **kwargs,
        )

    def algorithm_pod_spec(self, **kwargs) -> k8s_client.V1PodSpec:
        """Pod spec with the settings shared by all pods for algorithm runs."""
        cfg = self.algorithm_pod_config
        return k8s_client.V1PodSpec(
            restart_policy="Never",
            # Algorithms have no business with the Kubernetes API
            automount_service_account_token=False,
            service_account_name=cfg.get("service_account_name") or None,
            runtime_class_name=cfg.get("runtime_class_name") or None,
            security_context=cfg.get("pod_security_context") or None,
            affinity=self._node_affinity() if self.colocate_with_node else None,
            **kwargs,
        )

    def _node_affinity(self) -> k8s_client.V1Affinity:
        """
        Schedule a pod on the machine that runs the node pod, so that it can mount
        the node's ReadWriteOnce claims.
        """
        return k8s_client.V1Affinity(
            pod_affinity=k8s_client.V1PodAffinity(
                required_during_scheduling_ignored_during_execution=[
                    k8s_client.V1PodAffinityTerm(
                        label_selector=k8s_client.V1LabelSelector(
                            match_labels=self.node_pod_labels
                        ),
                        topology_key="kubernetes.io/hostname",
                    )
                ]
            )
        )

    def verify_isolation(self) -> tuple[bool, str]:
        image = (self.ctx.config.get("network_isolation") or {}).get(
            "probe_image"
        ) or ISOLATION_PROBE_IMAGE
        return validate_algorithm_isolation(
            core_api=self.core_api,
            task_namespace=self.task_namespace,
            log=self.log,
            labels={
                **self.algorithm_pod_labels,
                "role": AlgorithmStepType.CENTRAL_COMPUTE.value,
                "app": "v6-isolation-probe",
            },
            build_pod_spec=lambda containers: self.algorithm_pod_spec(
                containers=containers
            ),
            build_container=self.algorithm_container,
            image=image,
        )

    def _claim_mount(
        self,
        volumes: dict[str, k8s_client.V1Volume],
        claim_name: str,
        sub_path: str,
        mount_path: str,
        read_only: bool = False,
    ) -> k8s_client.V1VolumeMount:
        """
        Mount a file or folder from a PersistentVolumeClaim, adding a volume to
        ``volumes`` (keyed by claim name) if the claim has none yet.
        """
        if claim_name not in volumes:
            volumes[claim_name] = k8s_client.V1Volume(
                name=f"claim-{len(volumes)}",
                persistent_volume_claim=k8s_client.V1PersistentVolumeClaimVolumeSource(
                    claim_name=claim_name
                ),
            )
        return k8s_client.V1VolumeMount(
            name=volumes[claim_name].name,
            mount_path=mount_path,
            sub_path=sub_path or None,
            read_only=read_only,
        )

    def volumes_for(
        self, mounts: list[MountSpec]
    ) -> tuple[list[k8s_client.V1Volume], list[k8s_client.V1VolumeMount]]:
        volumes: dict[str, k8s_client.V1Volume] = {}
        volume_mounts = []
        for mount in mounts:
            if mount.storage.kind == StorageKind.TASK:
                claim = self.task_claim_name
                sub_path = join_sub_path(self.task_claim_sub_path, mount.sub_path)
            elif mount.storage.kind == StorageKind.CLAIM:
                claim = mount.storage.name
                sub_path = mount.sub_path
            else:
                raise PermanentAlgorithmStartFail(
                    f"Cannot mount host path '{mount.storage.name}' on Kubernetes. "
                    "Put the data on a volume claim instead."
                )
            volume_mounts.append(
                self._claim_mount(
                    volumes, claim, sub_path, mount.target, read_only=mount.read_only
                )
            )
        return list(volumes.values()), volume_mounts

    def _create_or_replace_secret(self, secret: k8s_client.V1Secret) -> None:
        try:
            self.core_api.create_namespaced_secret(
                namespace=self.task_namespace, body=secret
            )
        except ApiException as exc:
            if exc.status != 409:
                raise
            # Left behind by an earlier attempt of the same run
            self.core_api.replace_namespaced_secret(
                name=secret.metadata.name, namespace=self.task_namespace, body=secret
            )

    def _create_docker_login_secret(
        self, registries: list[RegistryCredentials], image: str, run_id: int
    ) -> k8s_client.V1Secret | None:
        dockerconfig = {
            "auths": {
                reg.registry: {
                    "username": reg.username,
                    "password": reg.password,
                    "auth": base64.b64encode(
                        f"{reg.username}:{reg.password}".encode()
                    ).decode(),
                }
                for reg in registries
            }
        }

        secret = k8s_client.V1Secret(
            metadata=k8s_client.V1ObjectMeta(
                name=f"docker-login-secret-run-id-{run_id}",
                namespace=self.task_namespace,
            ),
            type="kubernetes.io/dockerconfigjson",
            string_data={".dockerconfigjson": json.dumps(dockerconfig)},
        )

        try:
            self.core_api.create_namespaced_secret(
                namespace=self.task_namespace, body=secret
            )
        except Exception as exc:  # noqa: BLE001
            self.log.error(
                f"Error creating Docker login secret for image {image}: {exc}"
            )
            return None
        return secret

    def build_job(
        self, spec: RunSpec, docker_login_secret: k8s_client.V1Secret | None
    ) -> k8s_client.V1Job:
        volumes, volume_mounts = self.volumes_for(spec.mounts)
        container = self.algorithm_container(
            name=spec.name,
            image=spec.image,
            image_pull_policy=PULL_POLICIES[spec.pull_policy],
            tty=True,
            volume_mounts=volume_mounts,
            env=[
                k8s_client.V1EnvVar(name=key, value=value)
                for key, value in spec.env.items()
            ],
            env_from=(
                [
                    k8s_client.V1EnvFromSource(
                        secret_ref=k8s_client.V1SecretReference(name=spec.name)
                    )
                ]
                if spec.secret_env
                else []
            ),
        )

        image_pull_secrets = None
        if docker_login_secret:
            image_pull_secrets = [
                k8s_client.V1LocalObjectReference(
                    name=docker_login_secret.metadata.name
                )
            ]

        return k8s_client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=k8s_client.V1ObjectMeta(
                name=spec.name,
                annotations=spec.metadata.to_dict(),
                labels=self.task_job_labels,
            ),
            spec=k8s_client.V1JobSpec(
                template=k8s_client.V1PodTemplateSpec(
                    metadata=k8s_client.V1ObjectMeta(
                        labels={
                            **self.algorithm_pod_labels,
                            "app": spec.name,
                            "role": spec.step.value,
                        }
                    ),
                    spec=self.algorithm_pod_spec(
                        containers=[container],
                        volumes=volumes,
                        image_pull_secrets=image_pull_secrets,
                    ),
                ),
                backoff_limit=TASK_START_RETRIES,
                ttl_seconds_after_finished=self.algorithm_pod_config.get(
                    "ttl_seconds_after_finished"
                ),
            ),
        )

    def start_run(
        self, spec: RunSpec, on_status_change: Callable[[RunStatus], None]
    ) -> RunStatus:
        if spec.secret_env:
            self._create_or_replace_secret(
                k8s_client.V1Secret(
                    metadata=k8s_client.V1ObjectMeta(name=spec.name),
                    string_data=spec.secret_env,
                )
            )

        docker_login_secret = None
        if spec.registries:
            docker_login_secret = self._create_docker_login_secret(
                spec.registries, spec.image, spec.metadata.run_id
            )

        job = self.build_job(spec, docker_login_secret)
        self.log.info(
            "[Algorithm run %s requested by org %s] Creating namespaced K8S job for"
            " task_id=%s.",
            spec.metadata.run_id,
            spec.metadata.init_org_id,
            spec.metadata.task_id,
        )
        self.batch_api.create_namespaced_job(namespace=self.task_namespace, body=job)

        status = self._wait_until_pod_running(
            spec.name, spec.metadata.run_id, on_status_change
        )
        if status not in (RunStatus.ACTIVE, RunStatus.FAILED, RunStatus.COMPLETED):
            # The pod is stuck (e.g. the image cannot be pulled): the job never
            # finishes by itself
            self.remove_run(spec.name, spec.metadata.run_id)
        return status

    def _wait_until_pod_running(
        self,
        name: str,
        run_id: int,
        on_status_change: Callable[[RunStatus], None],
    ) -> RunStatus:
        """
        Wait until the pod of a job is running or has ended.

        The pod event stream is watched for up to K8S_EVENT_STREAM_LOOP_TIMEOUT
        seconds at a time, and watched again as long as the pod is still starting,
        e.g. because a large image is being pulled. Statuses that are not final are
        passed to ``on_status_change``.
        """
        label = f"app={name}"
        w = watch.Watch()

        last_reported_status: RunStatus | None = None

        def report_intermediate_status(status: RunStatus) -> None:
            """Report a non-final status, skipping repeats: the pod event stream
            fires on every pod update, and each report is a request to HQ."""
            nonlocal last_reported_status
            if status == last_reported_status:
                return
            last_reported_status = status
            on_status_change(status)

        try:
            while True:
                for event in w.stream(
                    func=self.core_api.list_namespaced_pod,
                    namespace=self.task_namespace,
                    label_selector=label,
                    timeout_seconds=K8S_EVENT_STREAM_LOOP_TIMEOUT,
                ):
                    pod_phase: RunStatus = compute_run_pod_status(
                        pod=event["object"],
                        label=label,
                        log=self.log,
                        task_namespace=self.task_namespace,
                    )
                    if pod_phase == RunStatus.ACTIVE or RunStatus.has_finished(
                        pod_phase
                    ):
                        return pod_phase
                    report_intermediate_status(pod_phase)

                self.log.debug(
                    "Task run (label %s, namespace %s) event stream timeout reached. "
                    "Checking the cause...",
                    label,
                    self.task_namespace,
                )
                pod_list = self.core_api.list_namespaced_pod(
                    namespace=self.task_namespace, label_selector=label
                ).items
                if not pod_list:
                    self.log.error(f"No POD found for run {run_id}")
                    return RunStatus.UNKNOWN_ERROR

                pod_phase: RunStatus = compute_run_pod_status(
                    pod=pod_list[0],
                    label=label,
                    log=self.log,
                    task_namespace=self.task_namespace,
                )
                if pod_phase == RunStatus.ACTIVE or RunStatus.has_finished(pod_phase):
                    return pod_phase
                report_intermediate_status(pod_phase)
                self.log.debug(
                    "Task run (label %s, namespace %s) still pulling the algorithm "
                    "image. Waiting again for a new status update...",
                    label,
                    self.task_namespace,
                )
        finally:
            w.stop()

    def list_runs(self) -> list[RunInfo]:
        jobs = self.batch_api.list_namespaced_job(
            self.task_namespace, label_selector=self.task_job_label_selector
        )
        runs = []
        for job in jobs.items:
            if job.status.succeeded:
                state = RunState.SUCCEEDED
            elif job.status.failed:
                state = RunState.FAILED
            else:
                state = RunState.RUNNING
            runs.append(
                RunInfo(
                    name=job.metadata.name,
                    state=state,
                    metadata=RunMetadata.from_dict(job.metadata.annotations),
                )
            )
        return runs

    def run_exists(self, name: str) -> bool:
        pods = self.core_api.list_namespaced_pod(
            namespace=self.task_namespace, label_selector=f"app={name}"
        )
        return bool(pods.items)

    def logs(self, name: str) -> str:
        """
        Logs of all pods of a job, e.g. of multiple failed attempts, merged as one.
        """
        pods_tty_logs = []
        job_pods_list = self.core_api.list_namespaced_pod(
            self.task_namespace, label_selector=f"job-name={name}"
        )
        for job_pod in job_pods_list.items:
            self.log.info(
                f"Getting logs from POD {job_pod.metadata.name}, created by job {name}"
            )
            pod_log = self.core_api.read_namespaced_pod_log(
                name=job_pod.metadata.name,
                namespace=self.task_namespace,
                _preload_content=True,
            )
            pods_tty_logs.append(
                f"LOGS of POD {job_pod.metadata.name} (created by job "
                f"{name}) \n\n {pod_log} \n\n\n"
            )
        return "\n".join(pods_tty_logs)

    def stream_logs(self, name: str) -> Iterator[str]:
        pod_list = self.core_api.list_namespaced_pod(
            namespace=self.task_namespace, label_selector=f"app={name}"
        ).items
        if not pod_list:
            self.log.error(f"No POD found for {name}")
            return
        w = watch.Watch()
        try:
            yield from w.stream(
                func=self.core_api.read_namespaced_pod_log,
                name=pod_list[0].metadata.name,
                namespace=self.task_namespace,
            )
        finally:
            w.stop()

    def remove_run(self, name: str, run_id: int) -> None:
        delete_run_related_pods(
            run_id=run_id,
            container_name=name,
            namespace=self.task_namespace,
            core_api=self.core_api,
            batch_api=self.batch_api,
        )

    def host_reachable_url(self, url: str) -> str:
        return replace_localhost_for_k8s(
            url, os.environ.get("V6_K8S_NODE_NAME") or None
        )
