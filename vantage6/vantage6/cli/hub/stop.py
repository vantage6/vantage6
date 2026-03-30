import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall
from vantage6.cli.globals import DEFAULT_API_SERVICE_SYSTEM_FOLDERS, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
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
@click.option("--all", "all_hubs", flag_value=True, help="Stop all running hubs")
def cli_hub_stop(
    name: str | None,
    context: str | None,
    namespace: str | None,
    system_folders: bool,
    sandbox: bool,
    all_hubs: bool,
) -> None:
    """
    Stop a hub.
    """
    execute_stop(
        stop_function=_stop_hub,
        instance_type=InstanceType.HUB,
        infra_component=InfraComponentName.HUB,
        stop_all=all_hubs,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
        is_sandbox=sandbox,
    )


def _stop_hub(name: str, k8s_config: KubernetesConfig) -> None:
    info(f"Stopping hub '{name}'...")

    helm_uninstall(release_name=name, k8s_config=k8s_config)

    info(f"Hub '{name}' stopped successfully.")
