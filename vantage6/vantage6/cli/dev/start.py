import subprocess
import click

from vantage6.common import info
from vantage6.client import Client
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.dev.connect_store import connect_and_seed_local_store
from vantage6.cli.dev.utils import get_dev_server_context
from vantage6.common.globals import DEFAULT_API_PATH


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
@click.option(
    "-c",
    "--config",
    default=None,
    help="Path to configuration-file; overrides --name",
)
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
    name: str | None,
    config: str | None,
    server_image: str | None,
    node_image: str | None,
    store_image: str | None,
) -> None:
    """Starts running a demo-network.

    Select a server configuration to run its demo network. You should choose a
    server configuration that you created earlier for a demo network. If you
    have not created a demo network, you can run `v6 dev create-demo-network` to
    create one.
    """
    ctx = get_dev_server_context(config, name)

    # run the server
    info("Starting server...")
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
        system_folders=False,
    )

    # run the store
    info("Starting algorithm store...")
    cmd = ["v6", "algorithm-store", "start", "--name", f"{ctx.name}_store", "--user"]
    if store_image:
        cmd.extend(["--image", store_image])
    subprocess.run(cmd, check=True)

    # run all nodes that belong to this server
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [
        config.name for config in configs if config.name.startswith(f"{ctx.name}_node_")
    ]
    for name in node_names:
        cmd = ["v6", "node", "start", "--name", name]
        if node_image:
            cmd.extend(["--image", node_image])
        subprocess.run(cmd, check=True)

    # now that both server and store have been started, couple them
    info("Linking local algorithm store to server...")
    store_ctxs, _ = AlgorithmStoreContext.available_configurations(system_folders=False)
    store_ctx = [c for c in store_ctxs if c.name == f"{ctx.name}_store"][0]
    client = Client(
        "http://localhost",
        ctx.config["port"],
        ctx.config["api_path"],
        log_level="warn",
    )
    # TODO these credentials are hardcoded and may change if changed elsewhere. Link
    # them together so that they are guaranteed to be the same.
    USERNAME = "dev_admin"
    PASSWORD = "password"
    client.authenticate(USERNAME, PASSWORD)
    api_path = store_ctx.config.get("api_path", DEFAULT_API_PATH)
    local_store_url = f"http://localhost:{store_ctx.config['port']}"
    connect_and_seed_local_store(client, local_store_url, api_path)
    info("Done!")
