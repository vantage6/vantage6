import click

from vantage6.common import info

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.context import InstanceType
from vantage6.cli.globals import InfraComponentName


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration")
@click.option("--system", "system_folders", flag_value=True, help="Use system folders")
@click.option("--user", "system_folders", flag_value=False, help="Use user folders")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Attach to a sandbox environment"
)
def cli_server_attach(
    name: str | None,
    system_folders: bool,
    context: str,
    namespace: str,
    is_sandbox: bool,
) -> None:
    """
    Show the server logs in the current console.
    """
    info("Attaching to server logs...")
    attach_logs(
        name,
        instance_type=InstanceType.SERVER,
        infra_component=InfraComponentName.SERVER,
        system_folders=system_folders,
        context=context,
        namespace=namespace,
        is_sandbox=is_sandbox,
        additional_labels="component=vantage6-server",
    )
