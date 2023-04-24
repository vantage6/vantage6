"""
The vdev module contains the CLI commands for generating dummy server and node
instance(s). The following commands are available:

    * vdev create-collaboration
"""
import pandas as pd
import uuid
import click

from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from colorama import (Fore, Style)
from vantage6.common.globals import APPNAME
from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.common.context import AppContext
from vantage6.common import info, warning, error


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
        default which is 'http:/host.docker.internal'
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

    node_name = f"node_{org_id}"
    dir_data = dummy_data(node_name)
    app_data_dir = \
        AppContext.instance_folders('node', node_name, False)['data']
    path_to_data_dir = Path(app_data_dir)
    path_to_data_dir.mkdir(parents=True, exist_ok=True)
    full_path = str(path_to_data_dir.parent / f'demo_{node_name}.yaml')
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


def generate_node_configs(num_configs: int, server_url: str,
                          port: int) -> list[dict]:
    """Generates `num_configs` node configuration files.

    Parameters
    ----------
    num_configs : int
        Scalar integer to determine how many configurations to
        create.
    server_url : str
        Specify server url, for instance localhost in which case revert to
        default which is 'http:/host.docker.internal'.
    port : int
        Port to access, default reverts to '5000'

    Returns
    -------
    list[dict]
        List of dictionairies containing node configurations.
    """
    configs = []
    for i in range(num_configs):
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


@click.group(name="dev")
def cli_dev() -> None:
    """Subcommand `vdev`."""
    pass


@cli_dev.command(name="create-demo-network")
@click.option('--num-configs', 'num_configs', type=int, default=3,
              help='generate N node-configuration files')
@click.option('--server-url', 'server_url', type=str,
              default='http:/host.docker.internal', help='server url')
@click.option('--server-port', 'server_port', default=5000, help='server port')
@click.option('--server-name', 'server_name', default='default_server',
              help='')
def create_demo_network(num_configs: int, server_url: str,
                        server_port: int, server_name: str) -> dict:
    """Click command to generate `num_configs` node configuration files as well
    as server configuration instance.

    Parameters
    ----------
    num_configs : int
        Number of node configuration files to generate.
    server_url : str
        Specify server url, for instance localhost in which case revert to
        default which is 'http:/host.docker.internal'.
    server_port : int
        Port to access, default reverts to '5000'
    server_name : str
        Server name.

    Returns
    -------
    dict
        dictionairy with `num_configs` node configurations and single server
        configuration instance.
    """
    try:
        node_configs = generate_node_configs(num_configs, server_url,
                                             server_port)
        server_import_config = create_vserver_import_config(node_configs,
                                                            server_name)
        server_config = create_vserver_config(server_name, server_port)
        info(f"Created {Fore.GREEN}{num_configs} node configuration(s), \
             attaching them to {Fore.GREEN}{server_name}.")
    except FileExistsError as e:
        warning(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} \
                already exists!")
        error(e)
        exit(1)
    return {'node_configs': node_configs,
            'server_import_config': server_import_config,
            'server_config': server_config}
