import click
import requests

from vantage6.common import error, info
from vantage6.common.globals import (
    DEFAULT_API_PATH,
    HTTP_LOCALHOST,
    InstanceType,
    Ports,
)

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
def cli_algo_store_version(
    name: str, system_folders: bool, context: str, namespace: str, is_sandbox: bool
) -> None:
    """
    Print the version of the vantage6 algorithm store.
    """

    ctx = get_and_select_ctx(
        InstanceType.ALGORITHM_STORE,
        name,
        system_folders,
        context,
        namespace,
        is_sandbox,
    )
    store_config = ctx.config.get("store", {})

    port = store_config.get("port", Ports.DEV_ALGO_STORE.value)
    api_path = store_config.get("api_path", DEFAULT_API_PATH)
    if not port:
        error("No port found in algorithm store configuration.")
        return
    if not api_path:
        error("No API path found in algorithm store configuration.")
        return

    response = requests.get(f"{HTTP_LOCALHOST}:{port}{api_path}/version")
    if response.status_code != 200:
        error("Failed to get algorithm store version.")
        return
    algorithm_store_version = response.json().get("version", "")

    info("")
    info(f"Algorithm store version: {algorithm_store_version}")
    info(f"CLI version: {__version__}")
