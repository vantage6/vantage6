import sys

import click

from vantage6.common.globals import Ports

from vantage6.client import UserClient
from vantage6.client.utils import LogLevel

from vantage6.cli.test.common.diagnostic_runner import DiagnosticRunner
from vantage6.cli.utils import error


@click.command()
@click.option(
    "--hq-url",
    type=str,
    default=f"http://localhost:{Ports.SANDBOX_HQ}/hq",
    help="URL of HQ",
)
@click.option(
    "--auth-url",
    type=str,
    default=f"http://localhost:{Ports.SANDBOX_AUTH}",
    help="URL of the authentication service (Keycloak)",
)
@click.option(
    "--auth-realm",
    type=str,
    default="vantage6",
    help="Realm of the authentication service (Keycloak)",
)
@click.option(
    "--auth-client",
    type=str,
    default="public_client",
    help="Client ID of the authentication service (Keycloak)",
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
@click.option(
    "--private-key",
    type=str,
    default=None,
    help="Path to the private key for end-to-end encryption",
)
@click.option(
    "--session-id",
    type=int,
    default=1,
    help="ID of the session to use for the diagnostic test",
)
@click.option(
    "--database-label",
    type=str,
    default="olympic-athletes",
    help="Label of the database to use for the diagnostic test",
)
def cli_test_features(
    hq_url: str,
    auth_url: str,
    auth_realm: str,
    auth_client: str,
    collaboration: int,
    organizations: list[int] | None,
    all_nodes: bool,
    online_only: bool,
    private_key: str | None,
    session_id: int,
    database_label: str,
) -> list[dict]:
    """
    Run diagnostic checks on an existing vantage6 network.

    This command will create a task in the requested collaboration that will
    test the functionality of vantage6, and will report back the results.
    """
    if all_nodes and organizations:
        error("Cannot use --all-nodes and --organizations at the same time.")
        sys.exit(1)

    if all_nodes or not organizations:
        organizations = None

    client = UserClient(
        hq_url=hq_url,
        auth_url=auth_url,
        auth_realm=auth_realm,
        auth_client=auth_client,
        log_level=LogLevel.CRITICAL,
    )
    client.authenticate()
    client.setup_encryption(private_key)
    diagnose = DiagnosticRunner(
        client,
        collaboration,
        organizations,
        online_only,
        session_id,
        database_label,
    )
    res = diagnose()
    return res
