from pathlib import Path

import click
from colorama import Fore, Style

from vantage6.common import error
from vantage6.common.globals import InstanceType

from vantage6.cli.context import get_context
from vantage6.cli.context.hq import HQContext
from vantage6.cli.k8s_config import select_k8s_config
from vantage6.cli.sandbox.config.hub import SandboxHubConfigManager
from vantage6.cli.sandbox.start import execute_sandbox_start
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
    "--hq-image",
    type=str,
    default=None,
    help="HQ docker image to use when setting up resources",
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
    "--extra-hq-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional HQ configuration. This will be appended to the HQ "
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
    "--data-dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom data directory to use. This option is especially useful "
    "on WSL because of mount issues for default directories",
)
@click.option(
    "--with-prometheus", is_flag=True, default=False, help="Enable Prometheus"
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
    hq_image: str | None,
    ui_image: str | None,
    store_image: str | None,
    node_image: str | None,
    extra_hq_config: Path | None,
    extra_node_config: Path | None,
    extra_store_config: Path | None,
    extra_auth_config: Path | None,
    add_dataset: tuple[str, Path] | None,
    context: str | None,
    namespace: str | None,
    data_dir: str | None,
    local_chart_dir: Path | None,
    with_prometheus: bool,
) -> None:
    """
    Create a sandbox environment.
    """

    # Prompt for the k8s namespace and context
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    if data_dir is not None:
        data_dir = Path(data_dir)
        if not data_dir.exists():
            error(f"Data directory {data_dir} does not exist!")
            exit(1)

    hq_name = prompt_config_name(name)
    if HQContext.config_exists(hq_name, False, is_sandbox=True):
        error(f"Configuration {Fore.RED}{hq_name}{Style.RESET_ALL} already exists!")
        exit(1)

    sb_config_manager = SandboxHubConfigManager(
        hq_name=hq_name,
        hq_image=hq_image,
        ui_image=ui_image,
        store_image=store_image,
        extra_hq_config=extra_hq_config,
        extra_store_config=extra_store_config,
        extra_auth_config=extra_auth_config,
        k8s_config=k8s_config,
        with_prometheus=with_prometheus,
        custom_data_dir=data_dir,
    )

    sb_config_manager.generate_hq_configs()

    ctx = get_context(
        type_=InstanceType.HQ,
        name=hq_name,
        system_folders=False,
        is_sandbox=True,
    )

    execute_sandbox_start(
        click_ctx=click_ctx,
        ctx=ctx,
        hq_name=hq_name,
        k8s_config=k8s_config,
        num_nodes=num_nodes,
        initialize=True,
        node_image=node_image,
        extra_node_config=extra_node_config,
        add_dataset=add_dataset,
        custom_data_dir=data_dir,
        local_chart_dir=local_chart_dir,
    )
