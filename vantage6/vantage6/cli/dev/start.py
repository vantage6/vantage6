import subprocess
import click

from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.algostore.start import cli_algo_store_start
from vantage6.common.globals import InstanceType


@click.command()
@click_insert_context(type_=InstanceType.SERVER)
@click.option(
    "--server-image", type=str, default=None, help="Server Docker image to use"
)
@click.option("--node-image", type=str, default=None, help="Node Docker image to use")
@click.option(
    "--store-image", type=str, default=None, help="Algorithm Store Docker image to use"
)
@click.pass_context
def start_demo_network(
    click_ctx: click.Context,
    ctx: ServerContext,
    server_image: str,
    node_image: str,
    store_image: str,
) -> None:
    """Starts running a demo-network.

    Select a server configuration to run its demo network. You should choose a
    server configuration that you created earlier for a demo network. If you
    have not created a demo network, you can run `vdev create-demo-network` to
    create one.
    """
    # run the server
    click_ctx.invoke(
        cli_server_start,
        ctx=ctx,
        ip=None,
        port=None,
        image=server_image,
        start_ui=True,
        ui_port=None,
        start_rabbitmq=False,
        rabbitmq_image=None,
        keep=True,
        mount_src="",
        attach=False,
    )

    # run the store
    cmd = ["v6", "algorithm-store", "start", "--name", f"{ctx.name}_store"]
    if store_image:
        cmd.extend(["--image", store_image])
    subprocess.run(cmd)

    # run all nodes that belong to this server
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [
        config.name for config in configs if f"{ctx.name}_node_" in config.name
    ]
    for name in node_names:
        cmd = ["v6", "node", "start", "--name", name]
        if node_image:
            cmd.extend(["--image", node_image])
        subprocess.run(cmd)
