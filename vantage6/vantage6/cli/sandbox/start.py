import subprocess
import time
from pathlib import Path

import click
from colorama import Fore, Style

from vantage6.common import error, info, warning
from vantage6.common.globals import HTTP_LOCALHOST, InstanceType, Ports

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.sandbox.config.node import NodeDataset, NodeSandboxConfigManager
from vantage6.cli.sandbox.populate import populate_server_sandbox
from vantage6.cli.server.start import cli_server_start


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
    help="Re-initialize the sandbox. This will repopulate the server and create new "
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
@click_insert_context(type_=InstanceType.SERVER, is_sandbox=True)
@click.pass_context
def cli_sandbox_start(
    click_ctx: click.Context,
    ctx: ServerContext,
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
        server_name=ctx.name,
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
    ctx: ServerContext,
    server_name: str,
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
    cmd = [
        "v6",
        "auth",
        "start",
        "--name",
        f"{server_name}-auth.sandbox",
        "--user",
        "--context",
        k8s_config.context,
        "--namespace",
        k8s_config.namespace,
        "--sandbox",
        "--wait-ready",
    ]
    if local_chart_dir:
        cmd.extend(["--local-chart-dir", local_chart_dir])
    subprocess.run(cmd, check=True)
    # Note: the CLI auth start function is blocking until the auth service is ready,
    # so no need to wait for it to be ready here.

    # run the store. The store is started before the server so that the server can
    # couple to the store on startup.
    cmd = [
        "v6",
        "algorithm-store",
        "start",
        "--name",
        f"{ctx.name}-store.sandbox",
        "--user",
        "--context",
        k8s_config.context,
        "--namespace",
        k8s_config.namespace,
        "--sandbox",
    ]
    if local_chart_dir:
        cmd.extend(["--local-chart-dir", local_chart_dir])
    subprocess.run(cmd, check=True)

    # Then we need to start the server
    click_ctx.invoke(
        cli_server_start,
        ctx=ctx,
        name=ctx.name,
        system_folders=False,
        namespace=k8s_config.namespace,
        context=k8s_config.context,
        attach=False,
        local_chart_dir=local_chart_dir,
    )

    server_url = f"{ctx.config['server']['baseUrl']}{ctx.config['server']['apiPath']}"
    _wait_for_server_to_be_ready(server_url)

    # Then we need to populate the server
    if initialize:
        node_config_names = _initialize_sandbox(
            server_url=server_url,
            server_name=server_name,
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
            if config.name.startswith(f"{server_name}-node-")
        ]

    # Then start the nodes
    info("Starting nodes")
    for node_config_name in node_config_names:
        cmd = [
            "v6",
            "node",
            "start",
            "--name",
            node_config_name,
            "--sandbox",
        ]
        if local_chart_dir:
            cmd.extend(["--local-chart-dir", local_chart_dir])
        subprocess.run(cmd, check=True)

    # Print the authentication credentials
    _print_auth_credentials(server_name)


def _initialize_sandbox(
    server_url: str,
    server_name: str,
    num_nodes: int,
    ctx: ServerContext,
    node_image: str | None,
    extra_node_config: Path | None,
    add_dataset: tuple[str, Path] | None,
    k8s_config: KubernetesConfig,
    custom_data_dir: Path | None,
    with_prometheus: bool,
) -> list[str]:
    info("Populating server")
    node_details = populate_server_sandbox(
        server_url=server_url,
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

    # Create node config files from the nodes that were just registered in the server
    node_config_manager = NodeSandboxConfigManager(
        server_name=server_name,
        api_keys=api_keys,
        node_names=node_names,
        server_port=ctx.config["server"]["port"],
        node_image=node_image,
        extra_node_config=extra_node_config,
        extra_dataset=extra_dataset,
        k8s_config=k8s_config,
        custom_data_dir=custom_data_dir,
        with_prometheus=with_prometheus,
    )
    node_config_manager.generate_node_configs()

    return node_config_manager.node_config_names


def _print_auth_credentials(server_name: str) -> None:
    """
    Find user credentials to print, from the auth config file

    Parameters
    ----------
    server_name : str
        Name of the server.
    """
    auth_ctx = AuthContext(
        instance_name=f"{server_name}-auth",
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


def _wait_for_server_to_be_ready(server_url: str) -> None:
    """
    Wait for the server to be initialized.

    Parameters
    ----------
    server_url : str
        URL of the server.
    """
    info("Waiting for server to become ready...")
    client = Client(
        # TODO replace default API path global
        server_url=server_url,
        auth_url=f"{HTTP_LOCALHOST}:{Ports.SANDBOX_AUTH}",
        log_level=LogLevel.ERROR,
    )
    max_retries = 100
    wait_time = 3
    ready = False
    for _ in range(max_retries):
        try:
            result = client.util.get_server_health(silent_on_connection_error=True)
            if result and result.get("api"):
                info("Server is ready.")
                ready = True
                break
        except Exception:
            info("Waiting for server to be ready...")
            time.sleep(wait_time)

    if not ready:
        error("Server did not become ready in time. Exiting...")
        exit(1)
