import sys

import click

from vantage6.common.globals import Ports

from vantage6.client import UserClient

from vantage6.cli.test.common.diagnostic_runner import DiagnosticRunner
from vantage6.cli.utils import error


@click.command()
@click.option(
    "--server-url",
    type=str,
    default=f"http://localhost:{Ports.DEV_SERVER}/api",
    help="URL of the server",
)
@click.option(
    "--auth-url",
    type=str,
    default="http://localhost:8080",
    help="URL of the authentication server (Keycloak)",
)
@click.option(
    "--auth-realm",
    type=str,
    default="vantage6",
    help="Realm of the authentication server (Keycloak)",
)
@click.option(
    "--auth-client",
    type=str,
    default="public_client",
    help="Client ID of the authentication server (Keycloak)",
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
def cli_test_features(
    server_url: str,
    auth_url: str,
    auth_realm: str,
    auth_client: str,
    collaboration: int,
    organizations: list[int] | None,
    all_nodes: bool,
    online_only: bool,
    no_vpn: bool,
    private_key: str | None,
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

    client = UserClient(
        server_url=server_url,
        auth_url=auth_url,
        auth_realm=auth_realm,
        auth_client=auth_client,
        log_level="critical",
    )
    client.authenticate()
    client.setup_encryption(private_key)
    diagnose = DiagnosticRunner(client, collaboration, organizations, online_only)
    res = diagnose(base=True, vpn=not no_vpn)
    return res
