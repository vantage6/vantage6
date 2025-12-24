import time
from pathlib import Path

import click
from colorama import Fore, Style

from vantage6.common import error, info, warning
from vantage6.common.globals import HTTP_LOCALHOST, InstanceType, Ports

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import execute_cli_start
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.context.hq import HQContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.sandbox.config.node import NodeDataset, NodeSandboxConfigManager
from vantage6.cli.sandbox.populate import populate_hub_sandbox


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--local-chart-dir",
    type=click.Path(exists=True),
    default=None,
    help="Local chart repository to use.",
)
@click.option(
    "--re-initialize",
    is_flag=True,
    default=False,
    help="Re-initialize the sandbox. This will repopulate HQ and create new "
    "node configurations.",
)
@click.option(
    "--num-nodes",
    type=int,
    default=3,
    help="Generate this number of nodes in the development network. Only used if "
    "--re-initialize flag is provided.",
)
@click.option(
    "--node-image",
    type=str,
    default=None,
    help="Node image to use. Only used if --re-initialize flag is provided.",
)
@click.option(
    "--extra-node-config",
    type=click.Path("rb"),
    default=None,
    help="YAML File with additional node configuration. This will be "
    "appended to each of the node configuration files. Only used if --re-initialize "
    "flag is provided",
)
@click.option(
    "--add-dataset",
    type=(str, click.Path()),
    default=None,
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file. Only used if the --re-initialize flag "
    "is provided.",
)
@click.option(
    "--data-dir",
    "custom_data_dir",
    type=click.Path(exists=True),
    default=None,
    help="Path to a custom data directory to use. This option is especially useful "
    "on WSL because of mount issues for default directories. Only used if the "
    "--re-initialize flag is provided.",
)
@click_insert_context(type_=InstanceType.HQ, is_sandbox=True)
@click.pass_context
def cli_sandbox_start(
    click_ctx: click.Context,
    ctx: HQContext,
    context: str | None,
    namespace: str | None,
    local_chart_dir: Path | None,
    re_initialize: bool,
    num_nodes: int,
    node_image: str | None,
    extra_node_config: Path | None,
    add_dataset: tuple[str, Path] | None,
    custom_data_dir: Path | None,
) -> None:
    """
    Start a sandbox environment.
    """
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # TODO if re-initalize is specified, we must remove the existing node configs
    execute_sandbox_start(
        click_ctx=click_ctx,
        ctx=ctx,
        hq_name=ctx.name,
        k8s_config=k8s_config,
        num_nodes=num_nodes,
        initialize=re_initialize,
        node_image=node_image,
        extra_node_config=extra_node_config,
        add_dataset=add_dataset,
        custom_data_dir=custom_data_dir,
        local_chart_dir=local_chart_dir,
    )


def execute_sandbox_start(
    click_ctx: click.Context,
    ctx: HQContext,
    hq_name: str,
    k8s_config: KubernetesConfig,
    num_nodes: int,
    initialize: bool,
    node_image: str | None = None,
    extra_node_config: Path | None = None,
    add_dataset: tuple[str, Path] | None = None,
    custom_data_dir: Path | None = None,
    local_chart_dir: str | None = None,
) -> None:
    with_prometheus = ctx.config.get("prometheus", {}).get("enabled", False)

    # First we need to start the keycloak service
    execute_cli_start(
        command_name=CLICommandName.AUTH,
        name=f"{hq_name}-auth.sandbox",
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        system_folders=False,
        is_sandbox=True,
        extra_args=["--wait-ready"],
    )

    # run the store. The store is started before HQ so that HQ can
    # couple to the store on startup.
    execute_cli_start(
        command_name=CLICommandName.ALGORITHM_STORE,
        name=f"{hq_name}-store.sandbox",
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        system_folders=False,
        is_sandbox=True,
    )

    # Then we need to start HQ
    execute_cli_start(
        command_name=CLICommandName.HQ,
        name=ctx.name,
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        system_folders=False,
        is_sandbox=True,
    )

    hq_url = f"{ctx.config['hq']['baseUrl']}{ctx.config['hq']['apiPath']}"
    _wait_for_hq_to_be_ready(hq_url)

    # Then we need to populate HQ
    if initialize:
        node_config_names = _initialize_sandbox(
            hq_url=hq_url,
            hq_name=hq_name,
            num_nodes=num_nodes,
            ctx=ctx,
            node_image=node_image,
            extra_node_config=extra_node_config,
            add_dataset=add_dataset,
            k8s_config=k8s_config,
            custom_data_dir=custom_data_dir,
            with_prometheus=with_prometheus,
        )
    else:
        node_configs, _ = NodeContext.available_configurations(
            system_folders=False, is_sandbox=True
        )
        node_config_names = [
            config.name
            for config in node_configs
            if config.name.startswith(f"{hq_name}-node-")
        ]

    # Then start the nodes
    info("Starting nodes")
    for node_config_name in node_config_names:
        execute_cli_start(
            command_name=CLICommandName.NODE,
            name=node_config_name,
            k8s_config=k8s_config,
            local_chart_dir=local_chart_dir,
            system_folders=False,
            is_sandbox=True,
        )

    # Print the authentication credentials
    _print_auth_credentials(hq_name)


def _initialize_sandbox(
    hq_url: str,
    hq_name: str,
    num_nodes: int,
    ctx: HQContext,
    node_image: str | None,
    extra_node_config: Path | None,
    add_dataset: tuple[str, Path] | None,
    k8s_config: KubernetesConfig,
    custom_data_dir: Path | None,
    with_prometheus: bool,
) -> list[str]:
    info("Populating vantage6 hub")
    node_details = populate_hub_sandbox(
        hq_url=hq_url,
        auth_url=f"{HTTP_LOCALHOST}:{Ports.SANDBOX_AUTH}",
        number_of_nodes=num_nodes,
    )

    api_keys = [node["api_key"] for node in node_details]
    node_names = [node["name"] for node in node_details]

    extra_dataset = (
        NodeDataset(
            label=add_dataset[0],
            path=add_dataset[1],
        )
        if add_dataset is not None and add_dataset != ()
        else None
    )

    # Create node config files from the nodes that were just registered in the HQ
    node_config_manager = NodeSandboxConfigManager(
        hq_name=hq_name,
        api_keys=api_keys,
        node_names=node_names,
        hq_port=ctx.config["hq"]["port"],
        node_image=node_image,
        extra_node_config=extra_node_config,
        extra_dataset=extra_dataset,
        k8s_config=k8s_config,
        custom_data_dir=custom_data_dir,
        with_prometheus=with_prometheus,
    )
    node_config_manager.generate_node_configs()

    return node_config_manager.node_config_names


def _print_auth_credentials(hq_name: str) -> None:
    """
    Find user credentials to print, from the auth config file

    Parameters
    ----------
    hq_name : str
        Name of the HQ.
    """
    auth_ctx = AuthContext(
        instance_name=f"{hq_name}-auth",
        system_folders=False,
        is_sandbox=True,
    )
    auth_config = auth_ctx.config

    try:
        admin_user = auth_config["keycloak"]["realmImport"]["users"][0]
        username = admin_user["username"]
        password = admin_user["credentials"][0]["value"]
        info("--------------------------------")
        info("Login with the following credentials:")
        info(
            f"Open the browser at: {Fore.GREEN}{HTTP_LOCALHOST}:"
            f"{Ports.SANDBOX_UI.value}{Style.RESET_ALL}"
        )
        info(f"Username: {Fore.GREEN}{username}{Style.RESET_ALL}")
        info(f"Password: {Fore.GREEN}{password}{Style.RESET_ALL}")
        info("--------------------------------")
    except KeyError:
        warning("No user credentials found in the auth config.")


def _wait_for_hq_to_be_ready(hq_url: str) -> None:
    """
    Wait for the HQ to be initialized.

    Parameters
    ----------
    hq_url : str
        URL of the hq.
    """
    info("Waiting for HQ to become ready...")
    client = Client(
        hq_url=hq_url,
        auth_url=f"{HTTP_LOCALHOST}:{Ports.SANDBOX_AUTH}",
        log_level=LogLevel.ERROR,
    )
    max_retries = 100
    wait_time = 3
    ready = False
    for _ in range(max_retries):
        try:
            result = client.util.get_hq_health(silent_on_connection_error=True)
            if result and result.get("api"):
                info("HQ is ready.")
                ready = True
                break
        except Exception:
            info("Waiting for HQ to be ready...")
            time.sleep(wait_time)

    if not ready:
        error("HQ did not become ready in time. Exiting...")
        exit(1)
