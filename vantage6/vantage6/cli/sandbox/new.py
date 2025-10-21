from pathlib import Path

import click
from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.globals import Ports

from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.context.server import ServerContext
from vantage6.cli.sandbox.config.core import CoreSandboxConfigManager
from vantage6.cli.sandbox.start import execute_sandbox_start
from vantage6.cli.server.common import get_server_context
from vantage6.cli.utils import prompt_config_name


@click.command()
@click.option(
    "-n", "--name", default=None, type=str, help="Name for your development setup"
)
@click.option(
    "--num-nodes",
    type=int,
    default=3,
    help="Generate this number of nodes in the development network",
)
@click.option(
    "-p",
    "--server-port",
    type=int,
    default=Ports.DEV_SERVER.value,
    help=f"Port to run the server on. Default is {Ports.DEV_SERVER}.",
)
@click.option(
    "--ui-port",
    type=int,
    default=Ports.DEV_UI.value,
    help=f"Port to run the UI on. Default is {Ports.DEV_UI}.",
)
@click.option(
    "--algorithm-store-port",
    type=int,
    default=Ports.DEV_ALGO_STORE.value,
    help=f"Port to run the algorithm store on. Default is {Ports.DEV_ALGO_STORE}.",
)
@click.option(
    "--server-image",
    type=str,
    default=None,
    help="Server docker image to use when setting up resources for "
    "the development server",
)
@click.option(
    "--ui-image",
    type=str,
    default=None,
    help="UI docker image to specify in configuration files. Will be used on startup of"
    " the network",
)
@click.option(
    "--store-image",
    type=str,
    default=None,
    help="Algorithm store docker image to use when setting up resources for "
    "the development algorithm store",
)
@click.option(
    "--node-image",
    type=str,
    default=None,
    help="Node docker image to use when setting up resources for the development node",
)
@click.option(
    "--extra-server-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional server "
    "configuration. This will be appended to the server "
    "configuration file",
)
@click.option(
    "--extra-node-config",
    type=click.Path("rb"),
    default=None,
    help="YAML File with additional node configuration. This will be"
    " appended to each of the node configuration files",
)
@click.option(
    "--extra-store-config",
    type=click.Path("rb"),
    default=None,
    help="YAML File with additional algorithm store configuration. This will be"
    " appended to the algorithm store configuration file",
)
@click.option(
    "--extra-auth-config",
    type=click.Path("rb"),
    default=None,
    help="YAML File with additional auth configuration. This will be"
    " appended to the auth configuration file",
)
@click.option(
    "--add-dataset",
    type=(str, click.Path()),
    default=None,
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file.",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--k8s-node-name", default="docker-desktop", help="Kubernetes node name to use"
)
@click.option(
    "--data-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom data directory to use. This option is especially useful "
    "on WSL because of mount issues for default directories",
)
@click.option(
    "--local-chart-dir",
    type=click.Path(exists=True),
    default=None,
    help="Local chart repository to use.",
)
@click.pass_context
def cli_new_sandbox(
    click_ctx: click.Context,
    name: str,
    num_nodes: int,
    server_port: int,
    ui_port: int,
    algorithm_store_port: int,
    server_image: str | None,
    ui_image: str | None,
    store_image: str | None,
    node_image: str | None,
    extra_server_config: Path | None,
    extra_node_config: Path | None,
    extra_store_config: Path | None,
    extra_auth_config: Path | None,
    add_dataset: tuple[str, Path] | None,
    context: str | None,
    namespace: str | None,
    k8s_node_name: str,
    data_dir: str | None,
    local_chart_dir: Path | None,
) -> None:
    """
    Create a sandbox environment.
    """

    # Prompt for the k8s namespace and context
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    if data_dir is not None:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            error(f"Data directory {data_dir} does not exist!")
            exit(1)

    server_name = prompt_config_name(name)
    if ServerContext.config_exists(server_name, False, is_sandbox=True):
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} already exists!")
        exit(1)

    sb_config_manager = CoreSandboxConfigManager(
        server_name=server_name,
        server_port=server_port,
        ui_port=ui_port,
        algorithm_store_port=algorithm_store_port,
        server_image=server_image,
        ui_image=ui_image,
        store_image=store_image,
        extra_server_config=extra_server_config,
        extra_store_config=extra_store_config,
        extra_auth_config=extra_auth_config,
        context=context,
        namespace=namespace,
        k8s_node_name=k8s_node_name,
        custom_data_dir=data_dir,
    )

    sb_config_manager.generate_server_configs()

    ctx = get_server_context(server_name, False, ServerContext, is_sandbox=True)

    execute_sandbox_start(
        click_ctx=click_ctx,
        ctx=ctx,
        server_name=server_name,
        context=context,
        namespace=namespace,
        num_nodes=num_nodes,
        initialize=True,
        node_image=node_image,
        k8s_node_name=k8s_node_name,
        extra_node_config=extra_node_config,
        add_dataset=add_dataset,
        custom_data_dir=data_dir,
        local_chart_dir=local_chart_dir,
    )
