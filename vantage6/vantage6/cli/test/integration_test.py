from pathlib import Path

import click

from vantage6.common.globals import Ports

from vantage6.cli.sandbox.new import cli_new_sandbox
from vantage6.cli.sandbox.remove import cli_sandbox_remove
from vantage6.cli.sandbox.stop import cli_sandbox_stop
from vantage6.cli.test.feature_tester import cli_test_features
from vantage6.cli.utils import check_config_name_allowed, info, prompt_config_name


@click.command()
@click.option(
    "-n", "--name", default=None, type=str, help="Name for your development setup"
)
@click.option("--hq-image", type=str, default=None, help="HQ Docker image to use")
@click.option(
    "--store-image", type=str, default=None, help="Algorithm store Docker image to use"
)
@click.option("--node-image", type=str, default=None, help="Node Docker image to use")
@click.option(
    "--extra-hq-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional HQ configuration. This will be appended to the HQ "
    "configuration file",
)
@click.option(
    "--extra-store-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional algorithm store configuration. This will be "
    "appended to the algorithm store configuration file",
)
@click.option(
    "--extra-auth-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional auth configuration. This will be appended to the "
    "auth configuration file",
)
@click.option(
    "--extra-node-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional node configuration. This will be appended to the "
    "node configuration file",
)
@click.option(
    "--keep",
    type=bool,
    default=False,
    help="Keep the sandbox running after finishing the test",
)
@click.pass_context
def cli_test_integration(
    click_ctx: click.Context,
    name: str,
    hq_image: str,
    store_image: str,
    node_image: str,
    extra_hq_config: Path,
    extra_store_config: Path,
    extra_auth_config: Path,
    extra_node_config: Path,
    keep: bool = False,
) -> list[dict]:
    """
    Create sandbox network and run diagnostic checks on it.

    This is a full integration test of the vantage6 network. It will create
    a sandbox network with some nodes, and then run the v6-diagnostics algorithm
    to test all functionality.
    """
    # get name for the sandbox - if not given - and check if it is allowed
    name = prompt_config_name(name)
    check_config_name_allowed(name)

    # create sandbox and start it
    click_ctx.invoke(
        cli_new_sandbox,
        name=name,
        num_nodes=3,
        hq_image=hq_image,
        store_image=store_image,
        node_image=node_image,
        extra_hq_config=extra_hq_config,
        extra_store_config=extra_store_config,
        extra_auth_config=extra_auth_config,
        extra_node_config=extra_node_config,
    )

    # run the diagnostic tests
    diagnose_results = click_ctx.invoke(
        cli_test_features,
        hq_url=f"http://localhost:{Ports.SANDBOX_HQ}/hq",
        auth_url=f"http://localhost:{Ports.SANDBOX_AUTH}",
        auth_realm="vantage6",
        auth_client="public_client",
        collaboration=1,
        organizations=None,
        all_nodes=True,
        online_only=False,
        private_key=None,
        session_id=1,
        database_label="olympic-athletes",
    )

    # clean up the test resources
    if not keep:
        click_ctx.invoke(cli_sandbox_stop, name=name)
        click_ctx.invoke(cli_sandbox_remove, name=name)
    else:
        info(f"Keeping the sandbox {name}. You can stop it with `v6 sandbox stop`")

    return diagnose_results
