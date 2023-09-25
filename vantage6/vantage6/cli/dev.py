"""
This module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev create-demo-network
    * vdev remove-demo-network
    * vdev start-demo-network
    * vdev stop-demo-network
"""
import click
import csv
import subprocess
import itertools

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from colorama import Fore, Style
from shutil import rmtree

from vantage6.common.globals import APPNAME
from vantage6.common import info, error, generate_apikey

from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.cli.context import ServerContext, NodeContext
from vantage6.cli.server import (
    click_insert_context,
    vserver_import,
    vserver_start,
    vserver_stop,
    vserver_remove,
    get_server_context
)
from vantage6.cli.node import vnode_stop
from vantage6.cli.utils import prompt_config_name, remove_file


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
    header = ['name', 'mask', 'weapon', 'age']
    data = [
        ['Raphael', 'red', 'sai', 44],
        ['Donatello', 'purple', 'bo staff', 60],
    ]

    data_file = dev_folder / f"df_{node_name}.csv"
    with open(data_file, 'w', encoding='UTF8', newline='') as f:
        writer = csv.writer(f)

        # write the header
        writer.writerow(header)

        # write the data
        for row in data:
            writer.writerow(row)

        f.close()

    info(f"Spawned dataset for {Fore.GREEN}{node_name}{Style.RESET_ALL}, "
         f"writing to {Fore.GREEN}{data_file}{Style.RESET_ALL}")
    return data_file


def create_node_config_file(server_url: str, port: int, config: dict,
                            server_name: str) -> None:
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
    server_name : str
        Configuration name of the dummy server.
    """
    environment = Environment(
        loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
        trim_blocks=True, lstrip_blocks=True, autoescape=True)
    template = environment.get_template("node_config.j2")

    # TODO: make this name specific to the server it connects
    node_name = config['node_name']
    folders = NodeContext.instance_folders('node', node_name, False)
    path_to_dev_dir = Path(folders['dev'] / server_name)
    path_to_dev_dir.mkdir(parents=True, exist_ok=True)
    dummy_datafile = create_dummy_data(node_name, path_to_dev_dir)

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


def generate_node_configs(num_nodes: int, server_url: str, port: int,
                          server_name: str) \
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
    server_name : str
        Configuration name of the dummy server.

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
            'node_name': f"{server_name}_node_{i + 1}"
        }
        create_node_config_file(server_url, port, config, server_name)
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
    server_config = template.render(
        port=port,
        jwt_secret_key=generate_apikey()
    )
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
    node_configs = generate_node_configs(num_nodes, server_url, server_port,
                                         server_name)
    server_import_config = create_vserver_import_config(node_configs,
                                                        server_name)
    server_config = create_vserver_config(server_name, server_port)
    return (node_configs, server_import_config, server_config)


@click.group(name="dev")
def cli_dev() -> None:
    """
    The `vdev` commands can be used to quickly manage a network with a server
    and several nodes for local testing.
    """


@cli_dev.command(name="create-demo-network")
@click.option('-n', '--name', default=None, type=str,
              help="Name for your development setup")
@click.option('--num-nodes', type=int, default=3,
              help='Generate this number of nodes in the development network')
@click.option('--server-url', type=str, default='http://host.docker.internal',
              help='Server URL to point to. If you are using Docker Desktop, '
              'the default http://host.docker.internal should not be changed.')
@click.option('-p', '--server-port', type=int, default=5000,
              help='Port to run the server on. Default is 5000.')
@click.option('-i', '--image', type=str, default=None,
              help='Server docker image to use when setting up resources for '
              'the development server')
def create_demo_network(name: str, num_nodes: int, server_url: str,
                        server_port: int, image: str = None) -> dict:
    """Creates a demo network.

    Creates server instance as well as its import configuration file. Server
    name is set to 'dev_default_server'. Generates `n` node configurations, but
    by default this is set to 3. Then runs a Batch import of
    organizations/collaborations/users and tasks.
    """
    server_name = prompt_config_name(name)
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
    ctx = get_server_context(server_name, True)
    vserver_import(ctx, server_import_config, False, image, '', False, True)
    return {
        "node_configs": node_config,
        "server_import_config": server_import_config,
        "server_config": server_config
    }


@cli_dev.command(name="start-demo-network")
@click_insert_context
@click.option('--server-image', type=str, default=None,
              help='Server Docker image to use')
@click.option('--node-image', type=str, default=None,
              help='Node Docker image to use')
def start_demo_network(
    ctx: ServerContext, server_image: str, node_image: str
) -> None:
    """Starts running a demo-network.

    Select a server configuration to run its demo network. You should choose a
    server configuration that you created earlier for a demo network. If you
    have not created a demo network, you can run `vdev create-demo-network` to
    create one.
    """
    # run the server
    vserver_start(
        ctx=ctx,
        ip=None,
        port=None,
        image=server_image,
        start_ui=False,
        ui_port=None,
        start_rabbitmq=False,
        rabbitmq_image=None,
        keep=True,
        mount_src='',
        attach=False
    )

    # run all nodes that belong to this server
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [
        config.name for config in configs if f'{ctx.name}_node_' in config.name
    ]
    for name in node_names:
        cmd = ["vnode", "start", "--name", name]
        if node_image:
            cmd.extend(["--image", node_image])
        subprocess.run(cmd)


@cli_dev.command(name="stop-demo-network")
@click_insert_context
def stop_demo_network(ctx: ServerContext) -> None:
    """ Stops a demo network's server and nodes.

    Select a server configuration to stop that server and the nodes attached
    to it.
    """
    # stop the server
    vserver_stop(name=ctx.name, system_folders=True, all_servers=False)

    # stop the nodes
    configs, _ = NodeContext.available_configurations(False)
    node_names = [
        config.name for config in configs if f'{ctx.name}_node_' in config.name
    ]
    for name in node_names:
        vnode_stop(name, system_folders=False, all_nodes=False, force=False)


@cli_dev.command(name="remove-demo-network")
@click_insert_context
@click.option('-f', "--force", type=bool, flag_value=True,
              help='Don\'t ask for confirmation')
def remove_demo_network(ctx: ServerContext, force: bool) -> None:
    """ Remove all related demo network files and folders.

    Select a server configuration to remove that server and the nodes attached
    to it.
    """

    # remove the server
    for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
        handler.close()
    vserver_remove(ctx, ctx.name, True, force)

    # removing the server import config
    info("Deleting demo import config file")
    server_configs = ServerContext.instance_folders("server", ctx.name,
                                                    system_folders=False)
    import_config_to_del = Path(server_configs['dev']) / f"{ctx.name}.yaml"
    remove_file(import_config_to_del, 'import_configuration')

    # also remove the server folder
    server_configs = ServerContext.instance_folders("server", ctx.name,
                                                    system_folders=True)
    server_folder = server_configs['data']
    if server_folder.is_dir():
        rmtree(server_folder)
    # TODO BvB 2023-07-31 can it happen that the server folder is not a
    # directory? What then?

    # remove the nodes
    configs, _ = NodeContext.available_configurations(system_folders=False)
    node_names = [
        config.name for config in configs if f'{ctx.name}_node_' in config.name
    ]
    for name in node_names:
        node_ctx = NodeContext(name, False)
        for handler in itertools.chain(node_ctx.log.handlers,
                                       node_ctx.log.root.handlers):
            handler.close()
        subprocess.run(["vnode", "remove", "-n", name, "--user", "--force"])

    # remove data files attached to the network
    data_dirs_nodes = NodeContext.instance_folders('node', '', False)['dev']
    rmtree(Path(data_dirs_nodes / ctx.name))
