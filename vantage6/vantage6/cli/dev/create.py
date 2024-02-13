from pathlib import Path
import csv
import yaml
import click
from jinja2 import Environment, FileSystemLoader
from colorama import Fore, Style

from vantage6.common.globals import APPNAME, InstanceType
from vantage6.common import info, error, generate_apikey

from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.cli.context.server import ServerContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.server.common import get_server_context
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.utils import prompt_config_name


def create_dummy_data(node_name: str, dev_folder: Path) -> Path:
    """Synthesize csv dataset.

    Parameters
    ----------
    node_name : str
        Name of node to be used as part of dataset.
    dev_folder : Path
        Path to the dev folder.

    Returns
    -------
    Path
        Directory the data is saved in.
    """
    header = ["name", "mask", "weapon", "age"]
    data = [
        ["Raphael", "red", "sai", 44],
        ["Donatello", "purple", "bo staff", 60],
    ]

    data_file = dev_folder / f"df_{node_name}.csv"
    with open(data_file, "w", encoding="UTF8", newline="") as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        # write the data
        for row in data:
            writer.writerow(row)

        f.close()

    info(
        f"Spawned dataset for {Fore.GREEN}{node_name}{Style.RESET_ALL}, "
        f"writing to {Fore.GREEN}{data_file}{Style.RESET_ALL}"
    )
    return data_file


def create_node_config_file(
    server_url: str, port: int, config: dict, server_name: str
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
    dummy_datafile = create_dummy_data(node_name, path_to_dev_dir)

    path_to_data_dir = Path(folders["data"])
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = Path(folders["config"] / f"{node_name}.yaml")

    if full_path.exists():
        error(f"Node configuration file already exists: {full_path}")
        exit(1)

    node_config = template.render(
        {
            "api_key": config["api_key"],
            "databases": {"default": dummy_datafile},
            "logging": {"file": f"{node_name}.log"},
            "port": port,
            "server_url": server_url,
            "task_dir": str(path_to_data_dir),
            "user_provided_config": config["user_defined_config"],
        }
    )

    try:
        with open(full_path, "x") as f:
            f.write(node_config)
    except Exception as e:
        error(f"Could not write node configuration file: {e}")
        exit(1)

    info(
        f"Spawned node for organization {Fore.GREEN}{config['org_id']}"
        f"{Style.RESET_ALL}"
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

    Returns
    -------
    list[dict]
        List of dictionaries containing node configurations.
    """
    configs = []
    extra_config = _read_extra_config_file(extra_node_config)
    for i in range(num_nodes):
        config = {
            "org_id": i + 1,
            "api_key": generate_apikey(),
            "node_name": f"{server_name}_node_{i + 1}",
            "user_defined_config": extra_config,
        }
        create_node_config_file(server_url, port, config, server_name)
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


def create_vserver_config(server_name: str, port: int, extra_config_file: Path) -> Path:
    """Creates server configuration file (YAML).

    Parameters
    ----------
    server_name : str
        Server name.
    port : int
        Server port.
    extra_config_file : Path
        Path to file with additional server configuration.

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

    template = environment.get_template("server_config.j2")
    server_config = template.render(
        port=port, jwt_secret_key=generate_apikey(), user_provided_config=extra_config
    )
    folders = ServerContext.instance_folders(
        instance_type="server", instance_name=server_name, system_folders=True
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


def demo_network(
    num_nodes: int,
    server_url: str,
    server_port: int,
    server_name: str,
    extra_server_config: Path,
    extra_node_config: Path,
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

    Returns
    -------
    tuple[list[dict], Path, Path]
        Tuple containing node, server import and server configurations.
    """
    node_configs = generate_node_configs(
        num_nodes, server_url, server_port, server_name, extra_node_config
    )
    server_import_config = create_vserver_import_config(node_configs, server_name)
    server_config = create_vserver_config(server_name, server_port, extra_server_config)
    return (node_configs, server_import_config, server_config)


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
    help="Server URL to point to. If you are using Docker Desktop, "
    "the default http://host.docker.internal should not be changed.",
)
@click.option(
    "-p",
    "--server-port",
    type=int,
    default=5000,
    help="Port to run the server on. Default is 5000.",
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
@click.pass_context
def create_demo_network(
    click_ctx: click.Context,
    name: str,
    num_nodes: int,
    server_url: str,
    server_port: int,
    image: str = None,
    extra_server_config: Path = None,
    extra_node_config: Path = None,
) -> dict:
    """Creates a demo network.

    Creates server instance as well as its import configuration file. Server
    name is set to 'dev_default_server'. Generates `n` node configurations, but
    by default this is set to 3. Then runs a Batch import of
    organizations/collaborations/users and tasks.
    """
    server_name = prompt_config_name(name)
    if not ServerContext.config_exists(server_name):
        demo = demo_network(
            num_nodes,
            server_url,
            server_port,
            server_name,
            extra_server_config,
            extra_node_config,
        )
        info(
            f"Created {Fore.GREEN}{len(demo[0])}{Style.RESET_ALL} node "
            f"configuration(s), attaching them to {Fore.GREEN}{server_name}"
            f"{Style.RESET_ALL}."
        )
    else:
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} already exists!")
        exit(1)
    (node_config, server_import_config, server_config) = demo
    ctx = get_server_context(server_name, True, ServerContext)
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
        f"server and nodes with {Fore.GREEN}v6 server start-demo-network"
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
    }
