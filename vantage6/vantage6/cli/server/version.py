import click
import requests

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli import __version__
from vantage6.cli.common.version import get_and_select_ctx
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Is this a sandbox environment?"
)
def cli_server_version(
    name: str, system_folders: bool, context: str, namespace: str, is_sandbox: bool
) -> None:
    """
    Print the version of the vantage6 server.
    """
    ctx = get_and_select_ctx(
        InstanceType.SERVER, name, system_folders, context, namespace, is_sandbox
    )
    server_config = ctx.config.get("server", {})
    base_url = server_config.get("baseUrl", "")
    api_path = server_config.get("apiPath", "")
    if not base_url:
        error("No base URL found in server configuration.")
        return
    if not api_path:
        error("No API path found in server configuration.")
        return

    response = requests.get(f"{base_url}{api_path}/version")
    if response.status_code != 200:
        error("Failed to get server version.")
        return
    server_version = response.json().get("version", "")

    info("")
    info(f"Server version: {server_version}")
    info(f"CLI version: {__version__}")
