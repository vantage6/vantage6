import sys
import click

from vantage6.common.globals import Ports
from vantage6.client import UserClient
from vantage6.cli.utils import error
from vantage6.cli.test.common.diagnostic_runner import DiagnosticRunner


@click.command()
@click.option("--host", type=str, default="http://localhost", help="URL of the server")
@click.option(
    "--port", type=int, default=Ports.DEV_SERVER.value, help="Port of the server"
)
@click.option("--api-path", type=str, default="/api", help="API path of the server")
@click.option(
    "--username",
    type=str,
    default="dev_admin",
    help="Username of vantage6 user account to create the task with",
)
@click.option(
    "--password",
    type=str,
    default="password",
    help="Password of vantage6 user account to create the task with",
)
@click.option(
    "--collaboration",
    type=int,
    default=1,
    help="ID of the collaboration to create the task in",
)
@click.option(
    "-o",
    "--organizations",
    type=int,
    default=[],
    multiple=True,
    help="ID(s) of the organization(s) to create the task for",
)
@click.option(
    "--all-nodes",
    is_flag=True,
    help="Run the diagnostic test on all nodes in the collaboration",
)
@click.option(
    "--online-only",
    is_flag=True,
    help="Run the diagnostic test on only nodes that are online",
)
@click.option("--no-vpn", is_flag=True, help="Don't execute VPN tests")
@click.option(
    "--private-key",
    type=str,
    default=None,
    help="Path to the private key for end-to-end encryption",
)
@click.option(
    "--mfa-code",
    type=str,
    help="Multi-factor authentication code. Use this if MFA is enabled on the "
    "server.",
)
def cli_test_features(
    host: str,
    port: int,
    api_path: str,
    username: str,
    password: str,
    collaboration: int,
    organizations: list[int] | None,
    all_nodes: bool,
    online_only: bool,
    no_vpn: bool,
    private_key: str | None,
    mfa_code: str | None,
) -> list[dict]:
    """
    Run diagnostic checks on an existing vantage6 network.

    This command will create a task in the requested collaboration that will
    test the functionality of vantage6, and will report back the results.
    """
    if all_nodes and organizations:
        error("Cannot use --all-nodes and --organization at the same time.")
        sys.exit(1)

    if all_nodes or not organizations:
        organizations = None

    client = UserClient(host=host, port=port, path=api_path, log_level="critical")
    client.authenticate(username=username, password=password, mfa_code=mfa_code)
    client.setup_encryption(private_key)
    diagnose = DiagnosticRunner(client, collaboration, organizations, online_only)
    res = diagnose(base=True, vpn=not no_vpn)
    return res
