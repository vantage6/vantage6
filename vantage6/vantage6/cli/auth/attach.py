import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config


@click.command()
@click.option(
    "-n", "--name", default=None, help="Name of the auth service to attach to"
)
@click.option("--system", "system_folders", flag_value=True, help="Use system folders")
@click.option("--user", "system_folders", flag_value=False, help="Use user folders")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Attach to a sandbox environment"
)
def cli_auth_attach(
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    is_sandbox: bool,
) -> None:
    """
    Show the server logs in the current console.
    """
    info("Attaching to auth logs...")

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    attach_logs(
        name,
        instance_type=InstanceType.AUTH,
        infra_component=InfraComponentName.AUTH,
        system_folders=system_folders,
        k8s_config=k8s_config,
        is_sandbox=is_sandbox,
    )
