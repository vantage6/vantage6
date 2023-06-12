"""
This module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev ---
    * vdev ----
    * vdev ---
    * vdev ---
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
from vantage6.common import info, warning, error, generate_apikey

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


def dummy_data(node_name: str) -> Path:
    """Synthesize csv dataset.

    Parameters
    ----------
    node_name : str
        Name of node to be used as part of dataset.

    Returns
    -------
    Path
        Directory the data is saved in.
    """
    cwd = Path.cwd()
    df = pd.DataFrame({'name': ['Raphael', 'Donatello'],
                       'mask': ['red', 'purple'],
                       'weapon': ['sai', 'bo staff']})
    dir_data = cwd / f"df_{node_name}.csv"
    df.to_csv(dir_data)
    info(f"Spawned dataset for {Fore.GREEN}{node_name}, writing to "
         f"{Fore.GREEN}{dir_data}{Style.RESET_ALL}")
    return dir_data


def create_node_config_file(org_id: int, server_url: str, port: int) -> dict:
    """Create a node configuration file (YAML).

    Creates a node configuration for a simulated organization. Organization ID
    is used for generating both the organization name and node_name as each
    organization only houses one node.

    Parameters
    ----------
    org_id : int
        Organization ID.
    server_url : str
        Url of the dummy server.
    port : int
        Port of the dummy server.

    Returns
    -------
    dict
        Dictionary of `organization_name`, `node_name` and `api_key` to
        be imported by `vserver import`.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True, lstrip_blocks=True, autoescape=True)
    template = environment.get_template("node_config.j2")

    # TODO: make this name specific to the server it connects
    node_name = f"demo_node_{org_id}"
    dir_data = dummy_data(node_name)

    folders = NodeContext.instance_folders('node', node_name, False)
    path_to_data_dir = Path(folders['data'])
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = str(folders['config'] / f'{node_name}.yaml')

    if full_path.exists():
        error(f"Node configuration file already exists: {full_path}")
        exit(1)

    api_key = generate_apikey()

    node_config = template.render({
        "api_key": api_key,
        "databases": {
            "default": dir_data
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

    info(f"Spawned node for organization {Fore.GREEN}{org_id}{Style.RESET_ALL}"
         )

    return {"org_id": org_id, "node_name": node_name, "api_key": api_key}


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
        configs.append(create_node_config_file(i, server_url, port))

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
    info(f"Organization {Fore.GREEN}0{Style.RESET_ALL} is the admin")

    server_import_config = template.render(organizations=organizations,
                                           collaboration=collaboration)
    folders = ServerContext.instance_folders("server", server_name, False)

    demo_dir = Path(folders['demo'])
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
                 server_name: str) -> tuple(list[dict], Path, Path):
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
    list
        List containing node, server import and server configurations.
    """
    # if not ServerContext.config_exists(server_name):
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
    name is set to 'default_server'. Generates `n` node configurations, but by
    default this is set to 3. Then runs a Batch import of
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
    mount_src : str, optional
        Vantage6 source location, this will overwrite the source code in the
        container. Useful for debugging/development., by default ''
    keep : bool, optional
        Wether to keep the image after finishing/crashing. Useful for
        debugging., by default False

    Returns
    -------
    dict
        Dictionary containing the locations of the node configurations,
        server import configuration and server configuration (YAML).
    """
    # TODO: make this work with multiple servers
    if not ServerContext.config_exists(server_name):
        demo = demo_network(num_nodes, server_url, server_port, server_name)
        info(f"Created {Fore.GREEN}{demo[0]}{Style.RESET_ALL} node "
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


# TODO: 5-6-2021: here we left off
@cli_dev.command(name="start-demo-network")
def start_demo_network(ip: str = None, port: int = None, image: str = None) \
        -> None:
    """Starts currently running demo-network, it once run as
    `start-demo-network`, it will display a list of available configurations
    to run, select the correct option, if using default settings it should be
    'default_server'.

    Parameters
    ----------
    ip : str, fixed
        ip interface to listen on, by default None
    port : int, fixed
        port to listen on, by default None
    image : str, fixed
        Server Docker image to use, by default None
    rabbitmq_image : str, fixed
        RabbitMQ docker image to use, by default None
    keep : bool, fixed
        Wether to keep the image after the server has finished, useful for
        debugging, by default False
    mount_src : str, fixed
        Path to the vantage6 package source, this overrides the source code in
        the container. This is useful when developing and testing the server.
        , by default ''
    attach : bool, fixed
        Wether to attach the server logs to the console after starting the
        server., by default False
    """
    configs, f1 = NodeContext.available_configurations(system_folders=False)
    ctx = get_server_context(server_name, S_ENV, True)
    handle_ = 'demo_'
    node_names = [config.name for config in configs if handle_ in config.name]
    vserver_start(ctx, ip, port, image, None, False, '', False)
    for index in range(len(node_names)):
        name = node_names[index]
        subprocess.run(["vnode", "start", "--name", name], shell=True)


@cli_dev.command(name="stop-demo-network")
@click.option("-n", "--name", default="default_server",
              help="Configuration name")
def stop_demo_network(name: str, environment: str = S_ENV,
                      system_folders: bool = True,
                      all_servers: bool = False) -> None:
    """Stops currently running demo-network. Defaults names for the server is
    'default_server', if run as `vdev stop-demo-network`. Defaults to stopping
    all the nodes spawned with the 'demo_' handle.

    Parameters
    ----------
    name : str
        Name of the spawned server executed from `vdev start-demo-network`
    environment : str, fixed
        DTAP environment to use, by default S_ENV
    system_folders : bool, fixed
        Wether to use system folders or not, by default True
    all_servers : bool, fixed
        Wether to stop all servers or not, by default False
    """
    vserver_stop(name, environment, system_folders, all_servers)
    # TODO: This will need to be dynamic... what happens if a config exists in
    # system?
    configs, f1 = NodeContext.available_configurations(False)
    handle_ = 'demo_'
    node_names = [config.name for config in configs if handle_ in config.name]
    for name in node_names:
        vnode_stop(name, system_folders=False, all_nodes=False, force=False)


def inner_remove_network(server_name: str, system_folders: bool) -> None:
    """This function does the bulk of removing the demo network. Removes all
    folders and anything within that was spawned by the `create_demo_network`.

    Parameters
    ----------
    server_name : str
        Name of the spawned server executed from `vdev start-demo-network`
    system_folders : bool
        Wether to use system folders or not.
    """
    handle_ = 'demo_'
    if system_folders:
        target = "--system"
    else:
        target = "--user"
    server_configs = ServerContext.instance_folders("server", server_name,
                                                    system_folders)
    if ServerContext.config_exists(server_name, S_ENV, system_folders):
        server_ctx = get_server_context(server_name, S_ENV, system_folders)
        # first we want to shut all the log files and root handlers...
        for handler in itertools.chain(server_ctx.log.handlers,
                                       server_ctx.log.root.handlers):
            handler.close()
        # now run vserver remove
        vserver_remove(server_ctx, server_name, S_ENV, system_folders)
    else:
        info(f"Skipping this configuration {server_name} in the {target[2:]} \
             folders")
        # traceback.print_exc()
    if 'demo' in server_configs:
        info("Deleting demo import config file")
        import_config_to_del = f"{server_configs['demo']}\\{server_name}.yaml"
        remove_file(import_config_to_del, 'import_configuration')
    # also want to remove the folder
    server_folder = server_configs['data']
    if server_folder.is_dir():
        shutil.rmtree(server_folder)
    # nodes
    configs, f1 = NodeContext.available_configurations(
        system_folders=system_folders
        )
    node_names = [config.name for config in configs if handle_ in config.name]
    if len(node_names):
        for name in node_names:
            node_ctx = NodeContext(name, N_ENV, system_folders)
            for handler in itertools.chain(node_ctx.log.handlers,
                                           node_ctx.log.root.handlers):
                handler.close()
            subprocess.run(["vnode", "remove", "-n", name, "-e", N_ENV,
                            target], shell=True)
            shutil.rmtree(f"{node_ctx.config_dir}\\{name}")


@cli_dev.command(name="remove-demo-network")
@click.option("-n", "--name", default="default_server",
              help="Configuration name")
def remove_demo_network(name: str) -> None:
    """Wrapper function for`inner_remove_network`, removes demo network. If no
    name is provided, the default option is chosen which is `default_server`.
    This function tries to remove the demo_network in in `system` as well
    as `user`system_folders.

    Parameters
    ----------
    name : str
        Name of the spawned server executed from `vdev start-demo-network`,
        default `default_server`.
    """
    try:
        inner_remove_network(server_name=name, system_folders=True)
    except Exception as e:
        print(e)
    else:
        inner_remove_network(server_name=name, system_folders=False)
