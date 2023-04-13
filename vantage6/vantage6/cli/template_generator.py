import jinja2
import pandas as pd
import uuid
import appdirs
import click

from pathlib import Path


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
    return dir_data


def create_node_config_file(org_id: int,
                            server_url: str,
                            port: int) -> dict:
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
        Dictionairy of organization_name, node_name and api_key to
        be imported by `vserver import`.
    """
    template_location = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_location)
    template = template_env.get_template("node_config.j2")

    node_name = f"node_{org_id}"
    dir_data = dummy_data(node_name)
    app_data_dir = Path(appdirs.AppDirs().user_data_dir)
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
        "task_dir": str(app_data_dir / node_name)
    })

    with open(f'{node_name}.yaml', 'w') as f:
        f.write(node_config)

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
        default which is 'http:/host.docker.internal'
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
    """Creates vserver configuration file (YAML).

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
    template_location = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_location)
    template = template_env.get_template("server_import_config.j2")
    organizations = []
    collaboration = {'name': 'demo', 'participants': []}
    for config in node_configs:
        org_id = config['org_id']
        org_data = {'name': f"org_{org_id}"}
        if org_id == 0:
            org_data['make_admin'] = True

        organizations.append(org_data)
        collaboration['participants'].append({'name': f"org_{org_id}",
                                              'api_key': config['api_key']})
    server_import_config = template.render(organizations=organizations,
                                           collaboration=collaboration)

    with open(f'{server_name}_import.yaml', 'w') as f:
        f.write(server_import_config)
    return Path(f'{server_name}_import.yaml')


def create_vserver_config(server_name: str, port: int) -> Path:
    """Creates vserver configuration yaml file

    Parameters
    ----------
    server_name : str
        Server name
    port : int
        Port to access, default reverts to '5000'

    Returns
    -------
    Path
        Path object where server configuration is stored.
    """
    template_location = jinja2.FileSystemLoader(searchpath="./")
    template_env = jinja2.Environment(loader=template_location)
    template = template_env.get_template("server_config.j2")
    server_config = template.render(data={'port': port})

    with open(f'{server_name}.yaml', 'w') as f:
        f.write(server_config)
    return Path(f'{server_name}.yaml')


@click.command()
@click.option('--num-configs', 'num_configs', type=int, default=3,
              help='generate N node-configuration files')
@click.option('--server-url', 'server_url', type=str,
              default='http:/host.docker.internal', help='server url')
@click.option('--server-port', 'server_port', default=5000, help='server port')
@click.option('--server-name', 'server_name', default='default_server',
              help='')
def demo_collab(num_configs: int, server_url: str, server_port: str,
                server_name: str) -> dict:
    """Click command to generate `num_configs` node configuration files as well
    as server configuration instance.

    Parameters
    ----------
    num_configs : int
        Number of node configuration files to generate.

    Returns
    -------
    dict
        dictionairy with `num_configs` node configurations and single server
        configuration instance.
    """
    node_configs = generate_node_configs(num_configs, server_url, server_port,
                                         server_name)
    server_import_config = create_vserver_import_config(node_configs,
                                                        server_name)
    server_config = create_vserver_config(server_name)
    return {'node_configs': node_configs,
            'server_import_config': server_import_config,
            'server_config': server_config}


server_name = "default_server"
server_url = "http:/host.docker.internal"
server_port = 5000
create_vserver_import_config(generate_node_configs(num_configs=5,
                                                   server_url=server_url,
                                                   port=server_port),
                             server_name=server_name)
create_vserver_config(server_name, server_port)
