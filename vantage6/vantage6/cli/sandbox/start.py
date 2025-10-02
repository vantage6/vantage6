import subprocess
import time

import click
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import InstanceType, Ports

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.context.server import ServerContext
from vantage6.cli.sandbox.config.node import NodeSandboxConfigManager
from vantage6.cli.sandbox.populate import populate_server_sandbox
from vantage6.cli.server.start import cli_server_start

LOCALHOST = "http://localhost"


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--re-initialize",
    is_flag=True,
    default=False,
    help="Re-initialize the sandbox",
)
@click.option(
    "--num-nodes",
    type=int,
    default=3,
    help="Generate this number of nodes in the development network. Only used if "
    "--re-initialize is set to True.",
)
@click_insert_context(
    type_=InstanceType.SERVER,
    include_name=True,
    include_system_folders=True,
    is_sandbox=True,
)
@click.pass_context
def cli_sandbox_start(
    click_ctx: click.Context,
    ctx: ServerContext,
    name: str,
    system_folders: bool,
    context: str | None,
    namespace: str | None,
    re_initialize: bool,
    num_nodes: int,
) -> None:
    """
    Start a sandbox environment.
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    execute_sandbox_start(
        click_ctx=click_ctx,
        ctx=ctx,
        server_name=ctx.name,
        context=context,
        namespace=namespace,
        num_nodes=num_nodes,
        initialize=re_initialize,
    )


def execute_sandbox_start(
    click_ctx: click.Context,
    ctx: ServerContext,
    server_name: str,
    context: str,
    namespace: str,
    num_nodes: int,
    initialize: bool,
    node_image: str | None = None,
) -> None:
    # First we need to start the keycloak service
    info("Starting keycloak service")
    cmd = [
        "v6",
        "auth",
        "start",
        "--name",
        f"{server_name}-auth.sandbox",
        "--user",
        "--context",
        context,
        "--namespace",
        namespace,
        "--sandbox",
    ]
    subprocess.run(cmd, check=True)
    # Note: the CLI auth start function is blocking until the auth service is ready,
    # so no need to wait for it to be ready here.

    # Then we need to start the server
    info("Starting vantage6 server")
    click_ctx.invoke(
        cli_server_start,
        ctx=ctx,
        name=ctx.name,
        system_folders=False,
        namespace=namespace,
        context=context,
        attach=False,
    )

    # run the store
    info("Starting algorithm store...")
    cmd = [
        "v6",
        "algorithm-store",
        "start",
        "--name",
        f"{ctx.name}-store.sandbox",
        "--user",
        "--context",
        context,
        "--namespace",
        namespace,
        "--sandbox",
    ]
    subprocess.run(cmd, check=True)

    server_url = f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}"
    wait_for_server_to_be_ready(server_url)

    # TODO also wait for store to be ready but maybe that needs to be done in the
    # populate function.

    # Then we need to populate the server
    info("Populating server")
    node_details = populate_server_sandbox(
        server_url=server_url,
        auth_url=f"{LOCALHOST}:{Ports.DEV_AUTH}",
        number_of_nodes=num_nodes,
    )

    import pprint

    print("Node details:")
    pprint.pprint(node_details)

    # Create node config files from the nodes that were just registered in the server
    node_config_manager = NodeSandboxConfigManager(
        server_name=server_name,
        num_nodes=num_nodes,
        server_port=ctx.config["server"]["port"],
        node_image=node_image,
        extra_node_config=None,
        extra_dataset=None,
        context=context,
        namespace=namespace,
    )
    node_config_manager.generate_node_configs()

    raise

    # Then start the import process
    info("Starting import process")
    # TODO: The clients and users are not deleted. The server will fail the import if
    # they already exist.
    node_details_from_server = click_ctx.invoke(
        cli_server_import,
        ctx=ctx,
        file=sb_config_manager.server_import_config_file,
        drop_all=False,
    )

    print(node_details_from_server)

    info("Updating node configuration files with API keys")
    # TODO: @bart this is where I left off. I tried to update the config files with the
    # API keys, it should be something like this:
    # for idx, node_detail in enumerate(node_details_from_server):
    #     node_config_file = node_config_files[idx]
    #     cm = ConfigurationManager.from_file(node_config_files, is_sandbox=True)
    #     cm.config["node"]["api_key"] = node_detail["api_key"]
    #     cm.save(node_config_file)
    # Reply from Bart: I think we should do this in a very different way: we start up
    # the server and use the client to generate nodes. Only then should we create the
    # node config files. It makes sense to me to try to sync the scripts from the dev
    # env with the sandbox env, so that we don't need to maintain two processes.

    click_ctx.invoke(
        cli_server_stop,
        name=server_name,
        context=context,
        namespace=namespace,
        system_folders=False,
        all_servers=True,
        is_sandbox=True,
    )

    info("Sandbox environment was set up successfully!")
    info("Start it using the following command:")
    info(f"{Fore.GREEN}v6 sandbox start{Style.RESET_ALL}")

    # find user credentials to print. Read from server import file
    with open(sb_config_manager.server_import_config_file, "r") as f:
        server_import_config = yaml.safe_load(f)

    try:
        user = server_import_config["organizations"][0]["users"][0]
        username = user["username"]
        password = user["password"]
        info("You can login with the following credentials:")
        info(f"Username: {Fore.GREEN}{username}{Style.RESET_ALL}")
        info(f"Password: {Fore.GREEN}{password}{Style.RESET_ALL}")
    except KeyError:
        # No user found, skip printing credentials
        pass


def wait_for_server_to_be_ready(server_url: str) -> None:
    """
    Wait for the server to be initialized.

    Parameters
    ----------
    server_url : str
        URL of the server.
    """
    client = Client(
        # TODO replace default API path global
        server_url=server_url,
        auth_url=f"{LOCALHOST}:{Ports.DEV_AUTH}",
        log_level=LogLevel.ERROR,
    )
    max_retries = 100
    wait_time = 3
    ready = False
    for _ in range(max_retries):
        try:
            result = client.util.get_server_health()
            if result and result.get("healthy"):
                info("Server is ready.")
                ready = True
                break
        except Exception:
            info("Waiting for server to be ready...")
            time.sleep(wait_time)

    if not ready:
        error("Server did not become ready in time. Exiting...")
        exit(1)
