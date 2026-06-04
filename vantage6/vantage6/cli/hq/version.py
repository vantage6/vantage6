import click
import requests

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli import __version__
from vantage6.cli.common.utils import extract_name_and_is_sandbox
from vantage6.cli.common.version import get_and_select_ctx
from vantage6.cli.globals import DEFAULT_API_SERVICE_SYSTEM_FOLDERS


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=DEFAULT_API_SERVICE_SYSTEM_FOLDERS,
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--sandbox", "is_sandbox", flag_value=True, help="Is this a sandbox environment?"
)
def cli_hq_version(
    name: str, system_folders: bool, context: str, namespace: str, is_sandbox: bool
) -> None:
    """
    Print the version of the vantage6 HQ.
    """
    name, is_sandbox = extract_name_and_is_sandbox(name, is_sandbox)
    if is_sandbox:
        system_folders = False
    ctx = get_and_select_ctx(
        InstanceType.HQ, name, system_folders, context, namespace, is_sandbox
    )
    hq_config = ctx.config.get("hq", {})
    base_url = hq_config.get("baseUrl", "")
    api_path = hq_config.get("apiPath", "")
    if not base_url:
        error("No base URL found in HQ configuration.")
        return
    if not api_path:
        error("No API path found in HQ configuration.")
        return

    response = requests.get(f"{base_url}{api_path}/version")
    if response.status_code != 200:
        error("Failed to get HQ version.")
        return
    hq_version = response.json().get("version", "")

    info("")
    info(f"HQ version: {hq_version}")
    info(f"CLI version: {__version__}")
