import click

from vantage6.cli.context.server import ServerContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.node.stop import cli_node_stop


@click.command()
@click_insert_context(type_="server")
@click.pass_context
def stop_demo_network(click_ctx: click.Context, ctx: ServerContext) -> None:
    """Stops a demo network's server and nodes.

    Select a server configuration to stop that server and the nodes attached
    to it.
    """
    # stop the server
    click_ctx.invoke(
        cli_server_stop, name=ctx.name, system_folders=True, all_servers=False
    )

    # stop the nodes
    configs, _ = NodeContext.available_configurations(False)
    node_names = [
        config.name for config in configs if f"{ctx.name}_node_" in config.name
    ]
    for name in node_names:
        click_ctx.invoke(
            cli_node_stop, name=name, system_folders=False, all_nodes=False, force=False
        )
