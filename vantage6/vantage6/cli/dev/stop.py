import click

from vantage6.cli.context import ServerContext, NodeContext
from vantage6.cli.server.cli import (
    click_insert_context,
    vserver_stop,
)
from vantage6.cli.node.stop import vnode_stop


@click.command()
@click_insert_context
def stop_demo_network(ctx: ServerContext) -> None:
    """ Stops a demo network's server and nodes.

    Select a server configuration to stop that server and the nodes attached
    to it.
    """
    # stop the server
    vserver_stop(name=ctx.name, system_folders=True, all_servers=False)

    # stop the nodes
    configs, _ = NodeContext.available_configurations(False)
    node_names = [
        config.name for config in configs if f'{ctx.name}_node_' in config.name
    ]
    for name in node_names:
        vnode_stop(name, system_folders=False, all_nodes=False, force=False)
