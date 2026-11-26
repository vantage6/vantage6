import sys

from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import error, info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.start import helm_install, prestart_checks
from vantage6.cli.common.utils import check_running
from vantage6.cli.context.node import NodeContext
from vantage6.cli.deployment.base import NodeDeployment
from vantage6.cli.globals import ChartName, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.node.common.private_key import (
    delete_private_key_secret,
    private_key_secret_exists,
    private_key_secret_name,
    read_private_key_secret,
    write_private_key_secret,
)


class KubernetesNodeDeployment(NodeDeployment):
    """Runs the node with its Helm chart in a Kubernetes namespace."""

    def __init__(
        self,
        ctx: NodeContext,
        name: str | None = None,
        system_folders: bool = False,
        context: str | None = None,
        namespace: str | None = None,
        k8s_config: KubernetesConfig | None = None,
        local_chart_dir: str | None = None,
        chart_version: str | None = None,
    ) -> None:
        super().__init__(ctx)
        self.config_name = name or ctx.name
        self.system_folders = system_folders
        self.k8s_config = k8s_config or select_k8s_config(
            context=context, namespace=namespace
        )
        self.local_chart_dir = local_chart_dir
        self.chart_version = chart_version

    @property
    def name(self) -> str:
        return self.ctx.helm_release_name

    def describe_target(self) -> str:
        return (
            f"Kubernetes context '{self.k8s_config.context}', namespace "
            f"'{self.k8s_config.namespace}'"
        )

    def prestart_checks(self) -> None:
        prestart_checks(
            self.ctx,
            InstanceType.NODE,
            self.config_name,
            self.system_folders,
            self.k8s_config,
        )
        if self.ctx.config.get("node", {}).get("encryption", {}).get("enabled"):
            self._check_private_key_secret()

    def _check_private_key_secret(self) -> None:
        """
        Exit if encryption is enabled but the node's private key secret is missing.
        The Helm chart mounts the secret; without it the node pod cannot start.
        """
        secret_name = private_key_secret_name(self.ctx)
        try:
            exists = private_key_secret_exists(self.ctx, self.k8s_config)
        except (RuntimeError, ApiException, HTTPError) as exc:
            warning(
                f"Could not check whether private key secret '{secret_name}' exists"
            )
            warning(str(exc))
            return
        if not exists:
            error(
                f"Encryption is enabled, but the private key secret '{secret_name}' "
                f"does not exist in namespace '{self.k8s_config.namespace}'."
            )
            info(
                "Create it with 'v6 node create-private-key', or use "
                "'v6 node create-private-key --from-file <path>' to store an "
                "existing key."
            )
            sys.exit(1)

    def start(self, image: str) -> None:
        helm_install(
            release_name=self.name,
            chart_name=ChartName.NODE,
            values_file=self.ctx.config_file,
            k8s_config=self.k8s_config,
            local_chart_dir=self.local_chart_dir,
            custom_values=[f"node.image={image}"],
            chart_version=self.chart_version,
        )

    def stop(self) -> None:
        from vantage6.cli.node.stop import _stop_node

        _stop_node(self.name, self.k8s_config, self.system_folders, self.ctx.is_sandbox)

    def is_running(self) -> bool:
        return check_running(
            self.name,
            InstanceType.NODE,
            self.config_name,
            self.system_folders,
            self.k8s_config,
        )

    def attach_logs(self) -> None:
        attach_logs(
            self.config_name,
            instance_type=InstanceType.NODE,
            infra_component=InfraComponentName.NODE,
            system_folders=self.system_folders,
            k8s_config=self.k8s_config,
            is_sandbox=self.ctx.is_sandbox,
        )

    def exec(self, command: list[str]) -> str:
        from vantage6.cli.node.version import (
            _exec_pod_command,
            _get_pod_name_for_helm_release,
        )

        pod = _get_pod_name_for_helm_release(self.name, self.k8s_config)
        return _exec_pod_command(pod, self.k8s_config, command)

    def read_private_key(self) -> bytes | None:
        return read_private_key_secret(self.ctx, self.k8s_config)

    def write_private_key(self, pem: bytes) -> None:
        write_private_key_secret(self.ctx, self.k8s_config, pem)

    def delete_private_key(self) -> bool:
        return delete_private_key_secret(self.ctx, self.k8s_config)
