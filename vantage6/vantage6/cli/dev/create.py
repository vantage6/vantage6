from importlib import resources as impresources
from pathlib import Path

import click
import pandas as pd
import yaml
from colorama import Fore, Style
from jinja2 import Environment, FileSystemLoader

from vantage6.common import ensure_config_dir_writable, error, generate_apikey, info
from vantage6.common.globals import APPNAME, InstanceType, Ports

import vantage6.cli.dev.data as data_dir
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import PACKAGE_FOLDER, DefaultDatasets
from vantage6.cli.server.common import get_server_context
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.utils import prompt_config_name


def create_node_data_files(
    num_nodes: int, server_name: str, dataset: tuple[str, Path]
) -> list[tuple[str, Path]]:
    """Create data files for nodes.

    Parameters
    ----------
    num_nodes : int
        Number of nodes to create data files for.
    server_name : str
        Name of the server.
    dataset : tuple[str, Path]
        Tuple containing the name and the path to the dataset.
    Returns
    -------
    list[tuple[str, Path]]
        List of the label and paths to the created data files.
    """
    info(f"Creating data files for {num_nodes} nodes.")
    data_files = []
    full_df = pd.read_csv(dataset[1])
    length_df = len(full_df)
    for i in range(num_nodes):
        node_name = f"{server_name}_node_{i + 1}"
        dev_folder = NodeContext.instance_folders("node", node_name, False)["dev"]
        data_folder = Path(dev_folder / server_name)
        data_folder.mkdir(parents=True, exist_ok=True)

        # Split the data over the nodes
        start = i * length_df // num_nodes
        end = (i + 1) * length_df // num_nodes
        data = full_df[start:end]
        data_file = data_folder / f"df_{dataset[0]}_{node_name}.csv"

        # write data to file
        data.to_csv(data_file, index=False)
        data_files.append((dataset[0], data_file))
    return data_files


def create_node_config_file(
    server_url: str,
    port: int,
    config: dict,
    server_name: str,
    datasets: list[tuple[str, Path]] = (),
) -> None:
    """Create a node configuration file (YAML).

    Creates a node configuration for a simulated organization. Organization ID
    is used for generating both the organization name and node_name as each
    organization only houses one node.

    Parameters
    ----------
    server_url : str
        Url of the dummy server.
    port : int
        Port of the dummy server.
    config : dict
        Configuration dictionary containing org_id, api_key, node name and
        additional user_defined_config.
    server_name : str
        Configuration name of the dummy server.
    datasets : list[tuple[str, Path]]
        List of tuples containing the labels and the paths to the datasets
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )
    template = environment.get_template("node_config.j2")

    # TODO: make this name specific to the server it connects
    node_name = config["node_name"]
    folders = NodeContext.instance_folders("node", node_name, False)
    path_to_dev_dir = Path(folders["dev"] / server_name)
    path_to_dev_dir.mkdir(parents=True, exist_ok=True)

    path_to_data_dir = Path(folders["data"])
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = Path(folders["config"] / f"{node_name}.yaml")

    if full_path.exists():
        error(f"Node configuration file already exists: {full_path}")
        exit(1)

    databases = [{dataset[0]: dataset[1]} for dataset in datasets]

    node_config = template.render(
        {
            "api_key": config["api_key"],
            "databases": databases,
            "logging": {"file": f"{node_name}.log"},
            "port": port,
            "server_url": server_url,
            "task_dir": str(path_to_data_dir),
            "user_provided_config": config["user_defined_config"],
        }
    )

    # Check that we can write the node config
    if not ensure_config_dir_writable():
        error("Cannot write configuration file. Exiting...")
        exit(1)

    Path(full_path).parent.mkdir(parents=True, exist_ok=True)
    with open(full_path, "x", encoding="utf-8") as f:
        f.write(node_config)

    info(
        f"Spawned node for organization {Fore.GREEN}{config['org_id']}{Style.RESET_ALL}"
    )


def _read_extra_config_file(extra_config_file: Path | None) -> str:
    """Reads extra configuration file.

    Parameters
    ----------
    extra_config_file : Path | None
        Path to file with additional configuration.

    Returns
    -------
    str
        Extra configuration file content
    """
    if extra_config_file:
        # read the YAML file as string, so it can be appended to the
        # configuration easily
        with open(extra_config_file, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def generate_node_configs(
    num_nodes: int,
    server_url: str,
    port: int,
    server_name: str,
    extra_node_config: Path | None,
    extra_datasets: list[tuple[str, Path]],
) -> list[dict]:
    """Generates ``num_nodes`` node configuration files.

    Parameters
    ----------
    num_nodes : int
        Integer to determine how many configurations to create.
    server_url : str
        Url of the dummy server.
    port : int
        Port of the dummy server.
    server_name : str
        Configuration name of the dummy server.
    extra_node_config : Path | None
        Path to file with additional node configuration.
    extra_datasets : list[tuple[str, Path]]
        List of tuples containing the labels and the paths to extra datasets

    Returns
    -------
    list[dict]
        List of dictionaries containing node configurations.
    """
    configs = []
    node_data_files = []
    extra_config = _read_extra_config_file(extra_node_config)

    data_directory = impresources.files(data_dir)

    # Add default datasets to the list of dataset provided
    for default_dataset in DefaultDatasets:
        extra_datasets.append(
            (default_dataset.name.lower(), data_directory / default_dataset.value)
        )

    # Check for duplicate dataset labels
    seen_labels = set()
    duplicates = [
        label
        for label in [dataset[0] for dataset in extra_datasets]
        if (label in seen_labels or seen_labels.add(label))
    ]

    if len(duplicates) > 0:
        error(
            f"Duplicate dataset labels found: {duplicates}. "
            f"Please make sure all dataset labels are unique."
        )
        exit(1)

    # create the data files for the nodes and get the path and label for each dataset
    for dataset in extra_datasets:
        node_data_files.append(create_node_data_files(num_nodes, server_name, dataset))

    for i in range(num_nodes):
        config = {
            "org_id": i + 1,
            "api_key": generate_apikey(),
            "node_name": f"{server_name}_node_{i + 1}",
            "user_defined_config": extra_config,
        }
        create_node_config_file(
            server_url,
            port,
            config,
            server_name,
            [files[i] for files in node_data_files],
        )
        configs.append(config)

    return configs


def create_vserver_import_config(node_configs: list[dict], server_name: str) -> Path:
    """Create server configuration import file (YAML).

    Utilized by the ``v6 server import`` command.

    Parameters
    ----------
    node_configs : list[dict]
        List of dictionaries containing the node configurations, returned from
        ``generate_node_configs()``.
    server_name : str
        Server name.

    Returns
    -------
    Path
        Path object where the server import configuration is stored.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )
    template = environment.get_template("server_import_config.j2")

    organizations = []
    collaboration = {"name": "demo", "participants": []}
    for config in node_configs:
        org_id = config["org_id"]
        org_data = {"name": f"org_{org_id}"}

        organizations.append(org_data)
        collaboration["participants"].append(
            {"name": f"org_{org_id}", "api_key": config["api_key"]}
        )
    organizations[0]["make_admin"] = True
    info(
        f"Organization {Fore.GREEN}{node_configs[0]['org_id']}"
        f"{Style.RESET_ALL} is the admin"
    )

    server_import_config = template.render(
        organizations=organizations, collaboration=collaboration
    )
    folders = ServerContext.instance_folders(InstanceType.SERVER, server_name, False)

    demo_dir = Path(folders["dev"])
    demo_dir.mkdir(parents=True, exist_ok=True)
    full_path = demo_dir / f"{server_name}.yaml"
    if full_path.exists():
        error(f"Server configuration file already exists: {full_path}")
        exit(1)

    try:
        with open(full_path, "x") as f:
            f.write(server_import_config)
            info(
                "Server import configuration ready, writing to "
                f"{Fore.GREEN}{full_path}{Style.RESET_ALL}"
            )
    except Exception as e:
        error(f"Could not write server import configuration file: {e}")
        exit(1)

    return full_path


def create_vserver_config(
    server_name: str,
    port: int,
    server_url: str,
    extra_config_file: Path,
    ui_image: str | None,
    ui_port: int,
    store_port: int,
) -> Path:
    """Creates server configuration file (YAML).

    Parameters
    ----------
    server_name : str
        Server name.
    port : int
        Server port.
    server_url : str
        Url of the server this
    extra_config_file : Path
        Path to file with additional server configuration.
    ui_image : str | None
        UI docker image to specify in configuration files. Will be used on startup of
        the network.
    ui_port : int
        Port to run the UI on.
    store_port : int
        Port to run the algorithm store on.

    Returns
    -------
    Path
        Path object where server configuration is stored.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    extra_config = _read_extra_config_file(extra_config_file)
    if ui_image is not None:
        if extra_config:
            extra_config += "\n"
        extra_config += f"images:\n  ui: {ui_image}"

    template = environment.get_template("server_config.j2")
    server_config = template.render(
        port=port,
        host_uri=server_url,
        user_provided_config=extra_config,
        ui_port=ui_port,
        store_port=store_port,
    )
    folders = ServerContext.instance_folders(
        instance_type=InstanceType.SERVER,
        instance_name=server_name,
        system_folders=False,
    )

    config_dir = Path(folders["config"] / server_name)
    config_dir.mkdir(parents=True, exist_ok=True)
    full_path = folders["config"] / f"{server_name}.yaml"
    if full_path.exists():
        error(f"Server configuration file already exists: {full_path}")
        exit(1)

    try:
        with open(full_path, "x") as f:
            f.write(server_config)
            info(
                "Server configuration read, writing to "
                f"{Fore.GREEN}{full_path}{Style.RESET_ALL}"
            )
    except Exception as e:
        error(f"Could not write server configuration file: {e}")
        exit(1)

    return full_path


def create_algo_store_config(
    server_name: str,
    server_url: str,
    server_port: int,
    store_port: int,
    extra_config_file: Path,
) -> Path:
    """Create algorithm store configuration file (YAML).

    Parameters
    ----------
    server_name : str
        Server name.
    server_url : str
        Url of the server this store connects to.
    server_port : int
        Port of the server this store connects to.
    port : int
        Port of the algorithm store.
    extra_config_file : Path
        Path to file with additional algorithm store configuration.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    extra_config = _read_extra_config_file(extra_config_file)

    template = environment.get_template("algo_store_config.j2")
    store_config = template.render(
        port=store_port,
        server_port=server_port,
        host_uri=server_url,
        user_provided_config=extra_config,
    )
    folders = AlgorithmStoreContext.instance_folders(
        instance_type=InstanceType.ALGORITHM_STORE,
        instance_name=f"{server_name}_store",
        system_folders=False,
    )

    config_dir = Path(folders["config"] / f"{server_name}_store")
    config_dir.mkdir(parents=True, exist_ok=True)
    full_path = folders["config"] / f"{server_name}_store.yaml"
    if full_path.exists():
        error(f"Algorithm store configuration file already exists: {full_path}")
        exit(1)

    try:
        with open(full_path, "x") as f:
            f.write(store_config)
            info(
                "Algorithm store configuration ready, writing to "
                f"{Fore.GREEN}{full_path}{Style.RESET_ALL}"
            )
    except Exception as e:
        error(f"Could not write algorithm store configuration file: {e}")
        exit(1)

    return full_path


def demo_network(
    num_nodes: int,
    server_url: str,
    server_port: int,
    server_name: str,
    extra_server_config: Path,
    extra_node_config: Path,
    extra_store_config: Path,
    ui_image: str,
    ui_port: int,
    algorithm_store_port: int,
    extra_datasets: list[tuple[str, Path]],
) -> tuple[list[dict], Path, Path]:
    """Generates the demo network.

    Parameters
    ----------
    num_nodes : int
        Integer to determine how many configurations to create.
    server_url : str
        Url of the dummy server.
    server_port : int
        Port of the dummy server.
    server_name : str
        Server name.
    extra_server_config : Path
        Path to file with additional server configuration.
    extra_node_config : Path
        Path to file with additional node configuration.
    extra_store_config : Path
        Path to file with additional algorithm store configuration.
    ui_image : str | None
        UI docker image to specify in configuration files. Will be used on startup of
        the network.
    ui_port : int
        Port to run the UI on.
    algorithm_store_port : int
        Port to run the algorithm store on.
    extra_datasets : list[tuple[str, Path]]
        List of tuples containing the labels and the paths to extra datasets

    Returns
    -------
    tuple[list[dict], Path, Path]
        Tuple containing node, server import and server configurations.
    """
    node_configs = generate_node_configs(
        num_nodes,
        server_url,
        server_port,
        server_name,
        extra_node_config,
        extra_datasets,
    )
    server_import_config = create_vserver_import_config(node_configs, server_name)
    server_config = create_vserver_config(
        server_name,
        server_port,
        server_url,
        extra_server_config,
        ui_image,
        ui_port,
        algorithm_store_port,
    )
    store_config = create_algo_store_config(
        server_name, server_url, server_port, algorithm_store_port, extra_store_config
    )
    return (node_configs, server_import_config, server_config, store_config)


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
    "--server-url",
    type=str,
    default="http://host.docker.internal",
    help="Server URL to point to. If you are using Docker Desktop, the default "
    "http://host.docker.internal should not be changed. If you are using Linux without"
    " Docker Desktop, you should set this to http://172.17.0.1",
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
    help=(f"Port to run the algorithm store on. Default is {Ports.DEV_ALGO_STORE}."),
)
@click.option(
    "-i",
    "--image",
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
    "--add-dataset",
    type=(str, click.Path()),
    default=(),
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file.",
)
@click.pass_context
def create_demo_network(
    click_ctx: click.Context,
    name: str,
    num_nodes: int,
    server_url: str,
    server_port: int,
    ui_port: int,
    algorithm_store_port: int,
    image: str = None,
    ui_image: str = None,
    extra_server_config: Path = None,
    extra_node_config: Path = None,
    extra_store_config: Path = None,
    add_dataset: list[tuple[str, Path]] = (),
) -> dict:
    """Creates a demo network.

    Creates server instance as well as its import configuration file. Server
    name is set to 'dev_default_server'. Generates `n` node configurations, but
    by default this is set to 3. Then runs a Batch import of
    organizations/collaborations/users and tasks.
    """
    server_name = prompt_config_name(name)
    if not ServerContext.config_exists(server_name, False):
        demo = demo_network(
            num_nodes,
            server_url,
            server_port,
            server_name,
            extra_server_config,
            extra_node_config,
            extra_store_config,
            ui_image,
            ui_port,
            algorithm_store_port,
            list(add_dataset),
        )
        info(
            f"Created {Fore.GREEN}{len(demo[0])}{Style.RESET_ALL} node "
            f"configuration(s), attaching them to {Fore.GREEN}{server_name}"
            f"{Style.RESET_ALL}."
        )
    else:
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} already exists!")
        exit(1)
    (node_config, server_import_config, server_config, store_config) = demo
    ctx = get_server_context(server_name, False, ServerContext)
    click_ctx.invoke(
        cli_server_import,
        ctx=ctx,
        file=server_import_config,
        drop_all=False,
        image=image,
        mount_src="",
        keep=False,
        wait=True,
    )
    info(
        "Development network was set up successfully! You can now start the "
        f"server and nodes with {Fore.GREEN}v6 dev start-demo-network"
        f"{Style.RESET_ALL}"
    )
    # find user credentials to print. Read from server import file
    with open(server_import_config, "r") as f:
        server_import_config = yaml.safe_load(f)

    try:
        user = server_import_config["organizations"][0]["users"][0]
        username = user["username"]
        password = user["password"]
        info(
            "You can login with the following credentials:\n"
            f"Username: {username}\n"
            f"Password: {password}\n"
        )
    except KeyError:
        # No user found, skip printing credentials
        pass

    return {
        "node_configs": node_config,
        "server_import_config": server_import_config,
        "server_config": server_config,
        "store_config": store_config,
    }
