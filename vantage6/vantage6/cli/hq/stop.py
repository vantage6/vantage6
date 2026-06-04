import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall
from vantage6.cli.globals import DEFAULT_API_SERVICE_SYSTEM_FOLDERS, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    default=DEFAULT_API_SERVICE_SYSTEM_FOLDERS,
    help="Search for configuration in system folders instead of user folders. "
    "This is the default.",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    help="Search for configuration in the user folders instead of system folders.",
)
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click.option("--all", "all_hqs", flag_value=True, help="Stop all running HQs")
def cli_hq_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    sandbox: bool,
    all_hqs: bool,
):
    """
    Stop a running HQ.
    """
    execute_stop(
        stop_function=_stop_hq,
        instance_type=InstanceType.HQ,
        infra_component=InfraComponentName.HQ,
        stop_all=all_hqs,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
        is_sandbox=sandbox,
    )


def _stop_hq(hq_name: str, k8s_config: KubernetesConfig) -> None:
    info(f"Stopping HQ '{hq_name}'...")

    # uninstall the helm release
    helm_uninstall(
        release_name=hq_name,
        k8s_config=k8s_config,
    )

    info(f"HQ '{hq_name}' stopped successfully.")
