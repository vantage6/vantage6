"""
The vdev module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev create-collaboration
"""
import pandas as pd
import uuid
import click
import questionary as q
import subprocess

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from colorama import Fore, Style

from vantage6.common.globals import APPNAME
from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.common.context import AppContext
from vantage6.common import info, warning, error
from vantage6.cli.context import ServerContext
from vantage6.cli.globals import (
    DEFAULT_SERVER_ENVIRONMENT
)
from vantage6.cli.server import (
    click_insert_context,
    vserver_import,
    vserver_start,
    vserver_stop
)
from vantage6.cli.context import NodeContext

from vantage6.cli.node import vnode_stop


def generate_apikey() -> str:
    """Creates random api_key using uuid.

    Returns
    -------
    str
        api_key
    """
    return str(uuid.uuid4())


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
    info(f"Spawned dataset for {Fore.GREEN}{node_name}, writing to \
         {Fore.GREEN}{dir_data}")
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
        Specify server url, for instance localhost in which case revert to
        default which is 'http://host.docker.internal'
    port : int
        Port to access, default reverts to '5000'

    Returns
    -------
    dict
        Dictionairy of `organization_name`, `node_name` and `api_key` to
        be imported by `vserver import`.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True, lstrip_blocks=True, autoescape=True)

    template = environment.get_template("node_config.j2")

    node_name = f"demo_node_{org_id}"
    dir_data = dummy_data(node_name)
    app_data_dir = \
        AppContext.instance_folders('node', node_name, False)['data']
    path_to_data_dir = Path(app_data_dir)
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = str(path_to_data_dir.parent / f'{node_name}.yaml')
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
        "task_dir": str(app_data_dir)
    })

    with open(full_path, 'x') as f:
        f.write(node_config)

    info(f"Spawned node for organization {Fore.GREEN}{org_id}")

    return {"org_id": org_id, "node_name": node_name, "api_key": api_key}


def generate_node_configs(num_configs: int | list[int], server_url: str,
                          port: int) -> list[dict]:
    """Generates `num_configs` node configuration files.

    Parameters
    ----------
    num_configs : int | list[int]
        If int, scalar integer to determine how many configurations to
        create. Else it is a list of integers corresponding, length of which
        matches how many nodes to spawn.
    server_url : str
        Specify server url, for instance localhost in which case revert to
        default which is 'http://host.docker.internal'.
    port : int
        Port to access, default reverts to '5000'

    Returns
    -------
    list[dict]
        List of dictionairies containing node configurations.
    """
    configs = []
    if isinstance(num_configs, int):
        rng = range(num_configs)
    elif isinstance(num_configs, list):
        rng = num_configs
    else:
        error('num_configs needs to be an integer corresponding to `N` \
              configs to be spawned OR list of integers.')
    for i in rng:
        configs.append(create_node_config_file(i, server_url, port))
    return configs


def create_vserver_import_config(node_configs: list[dict],
                                 server_name: str) -> Path:
    """Creates vserver configuration import file (YAML).
    Utilized by the `vserverimport` command.

    Parameters
    ----------
    node_configs : list[dict]
        List of dictionaries containing the node configurations, returned from
        `generate_node_configs()`.
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
        if org_id == 0:
            org_data['make_admin'] = True
            info(f"Organization {Fore.GREEN}{org_id} is the admin")

        organizations.append(org_data)
        collaboration['participants'].append({'name': f"org_{org_id}",
                                              'api_key': config['api_key']})
    server_import_config = template.render(organizations=organizations,
                                           collaboration=collaboration)
    server_data_dir = \
        AppContext.instance_folders(instance_type="server",
                                    instance_name=server_name,
                                    system_folders=False)['demo']
    path_to_data_dir = Path(server_data_dir)
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = str(path_to_data_dir / f'{server_name}.yaml')
    with open(full_path, 'x') as f:
        f.write(server_import_config)
        info(f"Server import configuration ready, writing to \
              {Fore.GREEN}{full_path}")
    return Path(full_path)


def create_vserver_config(server_name: str, port: int) -> Path:
    """Creates vserver configuration file (YAML).

    Parameters
    ----------
    server_name : str
        Server name.
    port : int
        Port to access, default reverts to '5000'.

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
    server_config_dir = \
        AppContext.instance_folders(instance_type='server',
                                    instance_name=server_name,
                                    system_folders=True)['config']
    path_to_server_config_dir = Path(server_config_dir / server_name)
    path_to_server_config_dir.mkdir(parents=True, exist_ok=True)
    full_path = \
        str(path_to_server_config_dir.parent / f'{server_name}.yaml')
    with open(full_path, 'x') as f:
        f.write(server_config)
        info(f"Server configuration read, writing to {Fore.GREEN}{full_path}")
    return Path(full_path)


def demo_network(num_configs: int | list[int], server_url: str,
                 server_port: int, server_name: str) -> list:
    """Generates the demo network.

    Parameters
    ----------
    num_configs : int | list[int]
        If int, scalar integer to determine how many configurations to
        create. Else it is a list of integers corresponding, length of which
        matches how many nodes to spawn.
    server_url : str
        Specify server url, for instance localhost in which case revert to
        default which is 'http://host.docker.internal'.
    server_port : int
        Port to access, default reverts to '5000'
    server_name : str
        Server name.

    Returns
    -------
    list
        List containing node, server import and server configurations.
    """
    node_configs = generate_node_configs(num_configs, server_url, server_port)
    server_import_config = create_vserver_import_config(node_configs,
                                                        server_name)
    server_config = create_vserver_config(server_name, server_port)
    return [node_configs, server_import_config, server_config]


@click.group(name="dev")
def cli_dev() -> None:
    """Subcommand `vdev`."""
    pass


@cli_dev.command(name="create-demo-network")
@click.option('--num-configs', 'num_configs', type=int, default=3,
              help='generate N node-configuration files')
@click_insert_context
def create_demo_network(ctx: ServerContext, num_configs: int,
                        server_url: str = 'http://host.docker.internal',
                        server_port: int = 5000,
                        server_name: str = 'default_server',
                        drop_all: bool = False, image: str = None,
                        mount_src: str = '', keep: bool = False) -> dict:
    """Synthesizes a demo network. Creates server instance as well as its
    import configuration file. Server name is set by default to
    'default_server'. Generates `N` node configurations, but by default this is
    set to 3. Then runs a Batch import of organizations/collaborations/users
    and tasks.

    Parameters
    ----------
    ctx : ServerContext
        Server context object
    num_configs : int
        Number of node configurations to spawn, by default 3.
    server_url : _type_, fixed
        Specify server url, for instance localhost in which case revert to,
        by default 'http://host.docker.internal'
    server_port : int, fixed
        Port to access, by default 5000
    server_name : str, fixed
        Name of server instance, by default 'default_server'
    drop_all : bool, fixed
        Wether to drop all data before importing, by default False
    image : str, fixed
        Node Docker image to use which contains the import script,
        by default None
    mount_src : str, fixed
        Vantage6 source location, this will overwrite the source code in the
        container. Useful for debugging/development., by default ''
    keep : bool, fixed
        Wether to keep the image after finishing/crashing. Useful for
        debugging., by default False

    Returns
    -------
    dict
        Dictionairy containing the locations of the node configurations,
        server import configuration and server configuration (YAML).
    """
    try:
        demo = demo_network(num_configs, server_url, server_port, server_name)
        info(f"Created {Fore.GREEN}{demo[0]} node configuration(s), \
             attaching them to {Fore.GREEN}{server_name}.")
    except FileExistsError as e:
        warning(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} \
                already exists!")
        warning(' ... Configuration already exists:')
        warning(f"     {e}")
        new_server_name = q.text("Please supply a new unique server \
                                  name:").ask()
        if new_server_name.count(" ") > 0:
            new_server_name = new_server_name.replace(" ", "-")
            info(f"Replaced spaces from configuration name: {new_server_name}")
        new_configs = [f"{new_server_name}_{id}" for id in range(num_configs)]
        demo = demo_network(new_configs, server_url, server_port,
                            new_server_name)
        info(f"Created {Fore.GREEN}{demo[0]} node configuration(s), \
             attaching them to {Fore.GREEN}{server_name}.")
    node_config = demo[0]
    server_import_config = demo[1]
    server_config = demo[2]
    vserver_import(ctx, server_import_config, drop_all, image, mount_src, keep)
    return {
        "node_configs": node_config,
        "server_import_config": server_import_config,
        "server_config": server_config
    }


@cli_dev.command(name="start-demo-network")
@click_insert_context
def start_demo_network(ctx: ServerContext, ip: str = None, port: int = None,
                       image: str = None, rabbitmq_image: str = None,
                       keep: bool = False, mount_src: str = '',
                       attach: bool = False) -> None:
    """Starts currently running demo-network, it once run as
    `start-demo-network`, it will display a list of available configurations
    to run, select the correct option, if using default settings it should be
    'default_server'.

    Parameters
    ----------
    ctx : ServerContext
        Server context import
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
    handle_ = 'demo_'
    node_names = [config.name for config in configs if handle_ in config.name]
    vserver_start(ctx, ip, port, image, rabbitmq_image, keep, mount_src,
                  attach)
    for index in range(len(node_names)):
        name = node_names[index]
        subprocess.run(["vnode", "start", "--name", name], shell=True)


@cli_dev.command(name="stop-demo-network")
@click.option("-n", "--name", default="default_server",
              help="Configuration name")
def stop_demo_network(name: str, environment: str = DEFAULT_SERVER_ENVIRONMENT,
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
        DTAP environment to use, by default DEFAULT_SERVER_ENVIRONMENT
    system_folders : bool, fixed
        Wether to use system folders or not, by default True
    all_servers : bool, fixed
        Wether to stop all servers or not, by default False
    """
    vserver_stop(name=name, environment=environment,
                 system_folders=system_folders, all_servers=all_servers)
    configs, f1 = NodeContext.available_configurations(system_folders=False)
    handle_ = 'demo_'
    node_names = [config.name for config in configs if handle_ in config.name]
    for name in node_names:
        vnode_stop(name, system_folders=False, all_nodes=False,
                   force=False)
