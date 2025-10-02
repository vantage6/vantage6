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
from vantage6.cli.context import get_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.sandbox.populate import populate_server_sandbox
from vantage6.cli.server.start import cli_server_start

LOCALHOST = "http://localhost"


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
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
) -> None:
    """
    Start a sandbox environment.
    """
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    info("Starting vantage6 core")
    click_ctx.invoke(
        cli_server_start,
        ctx=ctx,
        name=name,
        system_folders=system_folders,
        namespace=namespace,
        context=context,
        attach=False,
    )

    # run the store
    # info("Starting algorithm store...")
    # cmd = ["v6", "algorithm-store", "start", "--name", f"{ctx.name}-store", "--user"]
    # if store_image:
    #     cmd.extend(["--image", store_image])
    # subprocess.run(cmd, check=True)

    # # run all nodes that belong to this server
    configs, _ = NodeContext.available_configurations(
        system_folders=False, is_sandbox=True
    )
    node_names = [
        config.name for config in configs if config.name.startswith(f"{ctx.name}-node-")
    ]

    # TODO this should not be necessary, but somehow I get key errors when using the
    # from_external_config_file function. So this needs to be fixed
    ctx = get_context(InstanceType.NODE, node_names[0], False, is_sandbox=True)
    for name in node_names:
        # We cannot use the get_context function here because the node context is a
        # singleton, so we override the values using the `from_external_config_file`
        # function.
        file_ = NodeContext.find_config_file(
            InstanceType.NODE, name, False, is_sandbox=True
        )
        ctx = NodeContext.from_external_config_file(file_, is_sandbox=True)

        click_ctx.invoke(
            cli_node_start,
            ctx=ctx,
            name=ctx.name,
            system_folders=False,
            namespace=namespace,
            context=context,
            attach=False,
        )


def execute_sandbox_start(
    click_ctx: click.Context,
    ctx: ServerContext,
    server_name: str,
    server_port: int,
    context: str,
    namespace: str,
    num_nodes: int,
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

    wait_for_server_to_be_ready(server_port)

    # TODO also wait for store to be ready but maybe that needs to be done in the
    # populate function.

    # Then we need to populate the server
    info("Populating server")
    node_details = populate_server_sandbox(
        server_url=f"{LOCALHOST}:{server_port}/server",
        auth_url=f"{LOCALHOST}:{Ports.DEV_AUTH}",
        number_of_nodes=num_nodes,
    )

    import pprint

    print("Node details:")
    pprint.pprint(node_details)

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


def wait_for_server_to_be_ready(server_port: int) -> None:
    """
    Wait for the server to be initialized.

    Parameters
    ----------
    server_port : int
        Port of the server.
    """
    client = Client(
        # TODO replace default API path global
        server_url=f"{LOCALHOST}:{server_port}/server",
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
