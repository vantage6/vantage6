import subprocess
import click

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.utils import prompt_config_name
from vantage6.common import info
from vantage6.client import Client
from vantage6.cli.globals import COMMUNITY_STORE
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.server.start import cli_server_start
from vantage6.common.globals import DEFAULT_API_PATH, InstanceType
from vantage6.cli.context.server import ServerContext
from vantage6.cli.server.common import get_server_context
from vantage6.cli.context import get_context


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
    # cmd = ["v6", "algorithm-store", "start", "--name", f"{ctx.name}_store", "--user"]
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
