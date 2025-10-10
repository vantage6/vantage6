import itertools
from pathlib import Path
from shutil import rmtree

import click

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.remove import execute_remove
from vantage6.cli.configuration_create import select_configuration_questionnaire
from vantage6.cli.context import get_context
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.server.remove import cli_server_remove
from vantage6.cli.utils import remove_file


@click.command()
@click.option("-n", "--name", default=None, help="Name of the configuration.")
@click.option(
    "-c",
    "--config",
    default=None,
    help="Path to configuration-file; overrides --name",
)
@click.option(
    "--data-dir",
    "custom_data_dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom data directory to use. This option is especially useful "
    "on WSL because of mount issues for default directories. Use the same value as "
    "was provided when creating the sandbox.",
)
@click.pass_context
def cli_sandbox_remove(
    click_ctx: click.Context,
    name: str | None,
    config: str | None,
    custom_data_dir: Path | None,
) -> None:
    """Remove all related demo network files and folders.

    Select a server configuration to remove that server and the nodes attached
    to it.
    """

    if not name:
        try:
            name = select_configuration_questionnaire(
                type_=InstanceType.SERVER, system_folders=False, is_sandbox=True
            )
        except Exception:
            error("No configurations could be found!")
            exit()

    ctx = get_context(InstanceType.SERVER, name, system_folders=False, is_sandbox=True)

    # remove the server
    # Note that this also checks if the server is running. Therefore, it is prevented
    # that a running sandbox is removed.
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    click_ctx.invoke(
        cli_server_remove, ctx=ctx, name=name, system_folders=False, force=True
    )

    # removing the server import config
    info("Deleting demo import config file")
    server_configs = ServerContext.instance_folders(
        InstanceType.SERVER, ctx.name, system_folders=False
    )
    import_config_to_del = Path(server_configs["dev"]) / f"{ctx.name}.yaml"
    remove_file(import_config_to_del, "import_configuration")

    # also remove the server folder
    server_folder = server_configs["data"]
    if server_folder.is_dir():
        rmtree(server_folder)

    # remove the store folder
    store_configs = AlgorithmStoreContext.instance_folders(
        InstanceType.ALGORITHM_STORE,
        f"{ctx.name}-store",
        system_folders=False,
    )
    store_folder = store_configs["data"]
    if store_folder.is_dir():
        rmtree(store_folder)

    # remove the store config file
    AlgorithmStoreContext.LOGGING_ENABLED = False
    store_ctx = AlgorithmStoreContext(
        instance_name=f"{ctx.name}-store",
        system_folders=False,
        is_sandbox=True,
    )
    execute_remove(
        store_ctx,
        InstanceType.ALGORITHM_STORE,
        InfraComponentName.ALGORITHM_STORE,
        f"{ctx.name}-store",
        system_folders=False,
        force=True,
    )

    # remove the auth folder
    AuthContext.LOGGING_ENABLED = False
    auth_configs = AuthContext.instance_folders(
        InstanceType.AUTH, f"{ctx.name}-auth", system_folders=False
    )
    auth_folder = auth_configs["data"]
    if auth_folder.is_dir():
        rmtree(auth_folder)

    # remove the auth config file
    auth_ctx = AuthContext(
        instance_name=f"{ctx.name}-auth",
        system_folders=False,
        is_sandbox=True,
    )
    execute_remove(
        auth_ctx,
        InstanceType.AUTH,
        InfraComponentName.AUTH,
        f"{ctx.name}-auth",
        system_folders=False,
        force=True,
    )

    # remove the nodes
    NodeContext.LOGGING_ENABLED = False
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [
        config.name for config in configs if config.name.startswith(f"{ctx.name}-node-")
    ]
    for name in node_names:
        # Context clases are singletons, so we need to clear the cache to force
        # creation of a new instance. Otherwise, we *think* we get the ctx of another
        # node but we actually get the one from the previous node in the loop.
        if NodeContext in NodeContext._instances:
            del NodeContext._instances[NodeContext]

        node_ctx = NodeContext(
            instance_name=name,
            system_folders=False,
            is_sandbox=True,
            print_log_header=False,
            logger_prefix="",
            in_container=False,
        )
        for handler in itertools.chain(
            node_ctx.log.handlers, node_ctx.log.root.handlers
        ):
            handler.close()
        execute_remove(
            node_ctx,
            InstanceType.NODE,
            InfraComponentName.NODE,
            name,
            system_folders=False,
            force=True,
        )

    # remove data files attached to the network
    data_dirs_nodes = NodeContext.instance_folders("node", "", False)["dev"]
    rmtree(Path(data_dirs_nodes / ctx.name))

    # TODO remove the right data in the custom data directory if it is provided
