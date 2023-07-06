"""
This module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev create-demo-network
    * vdev remove-demo-network
    * vdev start-demo-network
    * vdev stop-demo-network
"""
import pandas as pd
import click
import subprocess
import shutil
import itertools

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from colorama import Fore, Style

from vantage6.common.globals import APPNAME
from vantage6.common import info, error, generate_apikey

from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.cli.context import ServerContext, NodeContext
from vantage6.cli.globals import (
    DEFAULT_SERVER_ENVIRONMENT as S_ENV,
    DEFAULT_NODE_ENVIRONMENT as N_ENV
)
from vantage6.cli.server import (
    vserver_import,
    vserver_start,
    vserver_stop,
    vserver_remove,
    get_server_context
)
from vantage6.cli.node import vnode_stop
from vantage6.cli.utils import remove_file

server_name = 'dev_default_server'
handle_ = 'dev_demo_'


def dummy_data(node_name: str, dev_folder: Path) -> Path:
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
    df = pd.DataFrame({'name': ['Raphael', 'Donatello'],
                       'mask': ['red', 'purple'],
                       'weapon': ['sai', 'bo staff']})
    dir_data = dev_folder / f"df_{node_name}.csv"
    df.to_csv(dir_data)
    info(f"Spawned dataset for {Fore.GREEN}{node_name}, writing to "
         f"{Fore.GREEN}{dir_data}{Style.RESET_ALL}")
    return dir_data


def create_node_config_file(server_url: str, port: int, config: dict) -> None:
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
        Configuration dictionary containing org_id, api_key and node name.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True, lstrip_blocks=True, autoescape=True)
    template = environment.get_template("node_config.j2")

    # TODO: make this name specific to the server it connects
    node_name = config['node_name']
    folders = NodeContext.instance_folders('node', node_name, False)
    dummy_datafile = dummy_data(node_name, folders['dev'])

    path_to_data_dir = Path(folders['data'])
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = Path(folders['config'] / f'{node_name}.yaml')

    if full_path.exists():
        error(f"Node configuration file already exists: {full_path}")
        exit(1)

    node_config = template.render({
        "api_key": config['api_key'],
        "databases": {
            "default": dummy_datafile
        },
        "logging": {
            "file": f'{node_name}.log'
        },
        "port": port,
        "server_url": server_url,
        "task_dir": str(path_to_data_dir)
    })

    try:
        with open(full_path, 'x') as f:
            f.write(node_config)
    except Exception as e:
        error(f"Could not write node configuration file: {e}")
        exit(1)

    info(f"Spawned node for organization {Fore.GREEN}{config['org_id']}"
         f"{Style.RESET_ALL}")


def generate_node_configs(num_nodes: int, server_url: str, port: int) \
        -> list[dict]:
    """Generates ``num_nodes`` node configuration files.

    Parameters
    ----------
    num_nodes : int
        Integer to determine how many configurations to create.
    server_url : str
        Url of the dummy server.
    port : int
        Port of the dummy server.

    Returns
    -------
    list[dict]
        List of dictionaries containing node configurations.
    """
    configs = []
    for i in range(num_nodes):
        config = {
            'org_id': i + 1,
            'api_key': generate_apikey(),
            'node_name': f"{handle_}node_{i + 1}"
        }
        create_node_config_file(server_url, port, config)
        configs.append(config)

    return configs


def create_vserver_import_config(node_configs: list[dict], server_name: str) \
        -> Path:
    """Creates vserver configuration import file (YAML).

    Utilized by the ``vserver import`` command.

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
        trim_blocks=True, lstrip_blocks=True, autoescape=True)
    template = environment.get_template("server_import_config.j2")

    organizations = []
    collaboration = {'name': 'demo', 'participants': []}
    for config in node_configs:
        org_id = config['org_id']
        org_data = {'name': f"org_{org_id}"}

        organizations.append(org_data)
        collaboration['participants'].append({'name': f"org_{org_id}",
                                              'api_key': config['api_key']})
    organizations[0]['make_admin'] = True
    info(f"Organization {Fore.GREEN}{node_configs[0]['org_id']}"
         f"{Style.RESET_ALL} is the admin")

    server_import_config = template.render(organizations=organizations,
                                           collaboration=collaboration)
    folders = ServerContext.instance_folders("server", server_name, False)

    demo_dir = Path(folders['dev'])
    demo_dir.mkdir(parents=True, exist_ok=True)
    full_path = demo_dir / f'{server_name}.yaml'
    if full_path.exists():
        error(f"Server configuration file already exists: {full_path}")
        exit(1)

    try:
        with open(full_path, 'x') as f:
            f.write(server_import_config)
            info("Server import configuration ready, writing to "
                 f"{Fore.GREEN}{full_path}{Style.RESET_ALL}")
    except Exception as e:
        error(f"Could not write server import configuration file: {e}")
        exit(1)

    return full_path


def create_vserver_config(server_name: str, port: int) -> Path:
    """Creates vserver configuration file (YAML).

    Parameters
    ----------
    server_name : str
        Server name.
    port : int
        Server port.

    Returns
    -------
    Path
        Path object where server configuration is stored.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True, lstrip_blocks=True, autoescape=True)
    template = environment.get_template("server_config.j2")
    server_config = template.render(port=port)
    folders = ServerContext.instance_folders(
        instance_type='server', instance_name=server_name,
        system_folders=True)

    config_dir = Path(folders['config'] / server_name)
    config_dir.mkdir(parents=True, exist_ok=True)
    full_path = folders["config"] / f'{server_name}.yaml'
    if full_path.exists():
        error(f"Server configuration file already exists: {full_path}")
        exit(1)

    try:
        with open(full_path, 'x') as f:
            f.write(server_config)
            info("Server configuration read, writing to "
                 f"{Fore.GREEN}{full_path}{Style.RESET_ALL}")
    except Exception as e:
        error(f"Could not write server configuration file: {e}")
        exit(1)

    return full_path


def demo_network(num_nodes: int, server_url: str, server_port: int,
                 server_name: str) -> tuple[list[dict], Path, Path]:
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

    Returns
    -------
    tuple[list[dict], Path, Path]
        Tuple containing node, server import and server configurations.
    """
    node_configs = generate_node_configs(num_nodes, server_url, server_port)
    server_import_config = create_vserver_import_config(node_configs,
                                                        server_name)
    server_config = create_vserver_config(server_name, server_port)
    return (node_configs, server_import_config, server_config)


@click.group(name="dev")
def cli_dev() -> None:
    """Subcommand `vdev`."""
    pass


@cli_dev.command(name="create-demo-network")
@click.option('-n', '--num-nodes', 'num_nodes', type=int, default=3,
              help='generate N node-configuration files')
@click.option('--server-url', 'server_url', type=str,
              default='http://host.docker.internal')
@click.option('-p', '--server-port', 'server_port', type=int, default=5000)
@click.option('-i', '--image', 'image', type=str, default=None)
def create_demo_network(num_nodes: int, server_url: str, server_port: int,
                        image: str = None) -> dict:
    """Synthesizes a demo network.

    Creates server instance as well as its import configuration file. Server
    name is set to 'dev_default_server'. Generates `n` node configurations, but
    by default this is set to 3. Then runs a Batch import of
    organizations/collaborations/users and tasks.

    Parameters
    ----------
    num_nodes : int, optional
        Number of node configurations to spawn, by default 3.
    server_url : str, optional
        Specify server url, for instance localhost in which case revert to,
        by default ``http://host.docker.internal``
    server_port : int, optional
        Port to access, by default 5000
    image : str, optional
        Node Docker image to use which contains the import script,
        by default None

    Returns
    -------
    dict
        Dictionary containing the locations of the node configurations,
        server import configuration and server configuration (YAML).
    """
    if not ServerContext.config_exists(server_name):
        demo = demo_network(num_nodes, server_url, server_port, server_name)
        info(f"Created {Fore.GREEN}{len(demo[0])}{Style.RESET_ALL} node "
             f"configuration(s), attaching them to {Fore.GREEN}{server_name}"
             f"{Style.RESET_ALL}.")
    else:
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} "
              "already exists!")
        exit(1)
    (node_config, server_import_config, server_config) = demo
    ctx = get_server_context(server_name, S_ENV, True)
    vserver_import(ctx, server_import_config, False, image, '', False)
    return {
        "node_configs": node_config,
        "server_import_config": server_import_config,
        "server_config": server_config
    }


@cli_dev.command(name="start-demo-network")
def start_demo_network(ip: str = None, port: int = None, image: str = None) \
        -> None:
    """Starts currently running demo-network, it once run as
    `start-demo-network`, it will display a list of available configurations
    to run, select the correct option, if using default settings it should be
    'dev_default_server'.

    Parameters
    ----------
    ip : str, fixed
        ip interface to listen on, by default None
    port : int, fixed
        port to listen on, by default None
    image : str, fixed
        Server Docker image to use, by default None
    """
    configs, _ = NodeContext.available_configurations(system_folders=False)
    ctx = get_server_context(server_name, S_ENV, True)
    node_names = [config.name for config in configs if handle_ in config.name]
    vserver_start(ctx, ip, port, image, None, False, '', False)
    for name in node_names:
        subprocess.run(["vnode", "start", "--name", name])


@cli_dev.command(name="stop-demo-network")
@click.option("-n", "--name", default=server_name,
              help="Configuration name")
def stop_demo_network(name: str) -> None:
    """Stops currently running demo-network. Defaults names for the server is
    'dev_default_server', if run as `vdev stop-demo-network`. Defaults to
    stopping all the nodes spawned with the 'demo_' handle.

    Parameters
    ----------
    name : str
        Name of the spawned server executed from `vdev start-demo-network`
    """
    vserver_stop(name=name, environment=S_ENV, system_folders=True,
                 all_servers=False)
    configs, _ = NodeContext.available_configurations(False)
    node_names = [config.name for config in configs if handle_ in config.name]
    for name in node_names:
        vnode_stop(name, system_folders=False, all_nodes=False, force=False)


@cli_dev.command(name="remove-demo-network")
@click.option("-n", "--name", default=server_name,
              help="Configuration name")
def remove_demo_network(server_name: str) -> None:
    """ Remove demo network.

    If no name is provided, the default option is chosen which is
    `dev_default_server`. This function tries to remove the demo_network in
    `system` as well as `user`system_folders.

    Parameters
    ----------
    server_name : str
        Name of the spawned server executed from `vdev start-demo-network`,
        default `dev_default_server`.
    """
    # removing the server
    if ServerContext.config_exists(server_name, S_ENV, True):
        server_ctx = get_server_context(server_name, S_ENV, True)
        # first we want to shut all the log files and root handlers...
        for handler in itertools.chain(server_ctx.log.handlers,
                                       server_ctx.log.root.handlers):
            handler.close()
        # now run vserver remove
        vserver_remove(server_ctx, server_name, S_ENV, True)

    # removing the server import config
    server_configs = ServerContext.instance_folders("server", server_name,
                                                    system_folders=True)
    if 'dev' in server_configs:
        info("Deleting demo import config file")
        import_config_to_del = \
            Path(server_configs['dev']) / f"{server_name}.yaml"
        remove_file(import_config_to_del, 'import_configuration')

    # also want to remove the server folder
    server_folder = server_configs['data']
    if server_folder.is_dir():
        shutil.rmtree(server_folder)

    # remove the nodes
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [config.name for config in configs if handle_ in config.name]
    for name in node_names:
        node_ctx = NodeContext(name, N_ENV, False)
        for handler in itertools.chain(node_ctx.log.handlers,
                                       node_ctx.log.root.handlers):
            handler.close()
        subprocess.run(["vnode", "remove", "-n", name, "-e", N_ENV,
                        "--user"])
        shutil.rmtree(Path(node_ctx.config_dir) / name)
