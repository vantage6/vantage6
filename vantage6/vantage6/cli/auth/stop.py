import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.stop import execute_stop, helm_uninstall, stop_port_forward
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS, InfraComponentName


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Search for configuration in system folders instead of user folders. "
    "This is the default.",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    help="Search for configuration in the user folders instead of system folders.",
)
def cli_auth_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
):
    """
    Stop a running auth service.
    """
    execute_stop(
        stop_function=_stop_auth,
        instance_type=InstanceType.AUTH,
        infra_component=InfraComponentName.AUTH,
        stop_all=False,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
    )


def _stop_auth(auth_name: str, namespace: str, context: str) -> None:
    info(f"Stopping auth {auth_name}...")

    # uninstall the helm release
    helm_uninstall(
        release_name=auth_name,
        context=context,
        namespace=namespace,
    )

    # stop the port forwarding for auth service
    stop_port_forward(
        service_name=f"{auth_name}-keycloak",
    )

    info(f"Auth {auth_name} stopped successfully.")
