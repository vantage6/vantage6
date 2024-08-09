import click

from vantage6.cli.context.node import NodeContext
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.node.stop import cli_node_stop
from vantage6.cli.algostore.stop import cli_algo_store_stop
from vantage6.cli.dev.utils import get_dev_server_context


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
@click.option(
    "-c",
    "--config",
    default=None,
    help="Path to configuration-file; overrides --name",
)
@click.pass_context
def stop_demo_network(
    click_ctx: click.Context, name: str | None, config: str | None
) -> None:
    """Stops a demo network's server and nodes.

    Select a server configuration to stop that server and the nodes attached
    to it.
    """
    ctx = get_dev_server_context(config, name)

    # stop the server
    click_ctx.invoke(
        cli_server_stop, name=ctx.name, system_folders=False, all_servers=False
    )

    # stop the algorithm store
    click_ctx.invoke(
        cli_algo_store_stop, name=f"{ctx.name}_store", system_folders=False
    )

    # stop the nodes
    configs, _ = NodeContext.available_configurations(False)
    node_names = [
        config.name for config in configs if config.name.startswith(f"{ctx.name}_node_")
    ]
    for name in node_names:
        click_ctx.invoke(
            cli_node_stop, name=name, system_folders=False, all_nodes=False, force=False
        )
