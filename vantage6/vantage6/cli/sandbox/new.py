import subprocess
import time
from importlib import resources as impresources
from pathlib import Path

import click
import pandas as pd
import yaml
from colorama import Fore, Style
from jinja2 import Environment, FileSystemLoader

from vantage6.common import error, info
from vantage6.common.globals import APPNAME, InstanceType, Ports

from vantage6.client import Client
from vantage6.client.utils import LogLevel

import vantage6.cli.sandbox.data as node_datafiles_dir
from vantage6.cli.common.new import new
from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import (
    PACKAGE_FOLDER,
    SERVER_IMPORT_TEMPLATE_FILE,
    DefaultDatasets,
)
from vantage6.cli.server.common import get_server_context
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.utils import prompt_config_name

LOCALHOST = "http://localhost"


class SandboxConfigManager:
    """
    Class to store the sandbox configurations.

    Parameters
    ----------
    server_name : str
        Name of the server.
    num_nodes : int
        Number of nodes to create.
    server_port : int
        Port of the server.
    ui_port : int
        Port of the UI.
    algorithm_store_port : int
        Port of the algorithm store.
    server_image : str | None
        Image of the server.
    node_image : str | None
        Image of the node.
    store_image : str | None
        Image of the algorithm store.
    ui_image : str | None
        Image of the UI.
    extra_server_config : Path | None
        Path to the extra server configuration file.
    extra_node_config : Path | None
        Path to the extra node configuration file.
    extra_store_config : Path | None
        Path to the extra algorithm store configuration file.
    extra_dataset : tuple[str, Path] | None
        List of tuples with the label and path to the dataset file.
    context : str | None
        Kubernetes context.
    namespace : str | None
        Kubernetes namespace.
    k8s_node_name : str
        Kubernetes node name.
    """

    def __init__(
        self,
        server_name: str,
        num_nodes: int,
        server_port: int,
        ui_port: int,
        algorithm_store_port: int,
        server_image: str | None,
        node_image: str | None,
        store_image: str | None,
        ui_image: str | None,
        extra_server_config: Path | None,
        extra_node_config: Path | None,
        extra_store_config: Path | None,
        extra_dataset: tuple[str, Path] | None,
        context: str | None,
        namespace: str | None,
        k8s_node_name: str,
    ) -> None:
        self.server_name = server_name
        self.num_nodes = num_nodes
        self.server_port = server_port
        self.ui_port = ui_port
        self.algorithm_store_port = algorithm_store_port
        self.server_image = server_image
        self.node_image = node_image
        self.store_image = store_image
        self.ui_image = ui_image
        self.extra_server_config = extra_server_config
        self.extra_node_config = extra_node_config
        self.extra_store_config = extra_store_config
        if extra_dataset:
            self.node_datasets = [extra_dataset]
        else:
            self.node_datasets = []
        self.context = context
        self.namespace = namespace

        self.node_configs = []
        self.node_config_files = []
        self.server_import_config_file = None
        self.server_config_file = None
        self.store_config_file = None
        self.k8s_node_name = k8s_node_name

        self._initialize_configs()

    def _initialize_configs(self) -> None:
        """Generates the demo network."""
        self._generate_node_configs()

        self._create_auth_config()

        self._create_vserver_import_config()

        self._create_vserver_config()

        self._create_algo_store_config()

    def _create_node_data_files(self, node_dataset: tuple[str, Path]) -> None:
        """
        Create data files for nodes.

        Parameters
        ----------
        node_dataset : tuple[str, Path]
            Tuple with the label and path to the dataset file.

        Returns
        -------
        list[tuple[str, Path]]
            List of tuples with the label and path to the dataset file.
        """
        info(f"Creating data files for {self.num_nodes} nodes.")
        db_label, db_path = node_dataset
        data_files = []
        full_df = pd.read_csv(db_path)
        length_df = len(full_df)
        for i in range(self.num_nodes):
            node_name = f"{self.server_name}_node_{i + 1}"
            dev_folder = NodeContext.instance_folders("node", node_name, False)["dev"]
            data_folder = Path(dev_folder / self.server_name)
            data_folder.mkdir(parents=True, exist_ok=True)

            # Split the data over the nodes
            start = i * length_df // self.num_nodes
            end = (i + 1) * length_df // self.num_nodes
            data = full_df[start:end]
            data_file = data_folder / f"df_{db_label}_{node_name}.csv"

            # write data to file
            data.to_csv(data_file, index=False)
            data_files.append((db_label, data_file))
        return data_files

    def _create_node_config_file(
        self, config: dict, datasets: list[tuple[str, Path]]
    ) -> None:
        """
        Create a node configuration file (YAML).

        Parameters
        ----------
        config : dict
            Configuration dictionary.
        datasets : list[tuple[str, Path]]
            List of tuples with the label and path to the dataset file.

        Returns
        -------
        Path
            Path to the node configuration file.
        """
        node_name = config["node_name"]
        folders = NodeContext.instance_folders("node", node_name, False)
        path_to_dev_dir = Path(folders["dev"] / self.server_name)
        path_to_dev_dir.mkdir(parents=True, exist_ok=True)

        path_to_data_dir = Path(folders["data"])
        path_to_data_dir.mkdir(parents=True, exist_ok=True)

        node_config = new(
            config_producing_func=self.__node_config_return_func,
            config_producing_func_args=(config, datasets, path_to_data_dir),
            name=node_name,
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.NODE,
            is_sandbox=True,
        )

        return node_config

    def __node_config_return_func(
        self,
        node_specific_config: dict,
        datasets: list[tuple[str, Path]],
        path_to_data_dir: Path,
    ) -> dict:
        """
        Return a dict with node configuration values to be used in creating the
        config file.
        """
        return {
            "node": {
                "proxyPort": 7676 + int(node_specific_config["org_id"]),
                "api_key": node_specific_config["api_key"],
                "image": (
                    self.node_image
                    # TODO v5+ update
                    or "harbor2.vantage6.ai/infrastructure/node:5.0.0a36"
                ),
                "logging": {
                    "file": f"{node_specific_config['node_name']}.log",
                },
                # TODO: the keycloak instance should be spun up together with the
                # server
                "keycloakUrl": (
                    "http://vantage6-auth-keycloak.default.svc.cluster.local"
                ),
                "keycloakRealm": "vantage6",
                "additional_config": node_specific_config["user_defined_config"],
                "dev": {
                    "task_dir_extension": str(path_to_data_dir),
                },
                "persistence": {
                    "tasks": {
                        "hostPath": str(path_to_data_dir),
                        "size": "1Gi",
                    },
                    "database": {
                        "size": "1Gi",
                    },
                },
                "databases": {
                    "fileBased": [
                        {
                            "name": dataset[0],
                            "uri": dataset[1],
                            "type": "csv",
                            "volumePath": Path(dataset[1]).parent,
                            "originalName": dataset[0],
                        }
                        # TODO there is an issue with supplying multiple datasets
                        for dataset in [datasets[0]]
                    ]
                },
                "server": {
                    "url": LOCALHOST,
                    "port": self.server_port,
                },
            },
        }

    @staticmethod
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

    def _generate_node_configs(self) -> None:
        """
        Generates ``num_nodes`` node configuration files.
        """
        node_data_files = []
        extra_config = self._read_extra_config_file(self.extra_node_config)

        data_directory = impresources.files(node_datafiles_dir)

        # Add default datasets to the list of dataset provided
        for default_dataset in DefaultDatasets:
            self.node_datasets.append(
                (
                    default_dataset.name.lower().replace("_", "-"),
                    data_directory / default_dataset.value,
                )
            )

        # Check for duplicate dataset labels
        seen_labels = set()
        duplicates = [
            label
            for label in [dataset[0] for dataset in self.node_datasets]
            if (label in seen_labels or seen_labels.add(label))
        ]

        if len(duplicates) > 0:
            error(
                f"Duplicate dataset labels found: {duplicates}. "
                f"Please make sure all dataset labels are unique."
            )
            exit(1)

        # create the data files for the nodes and get the path and label for each
        # dataset
        for dataset in self.node_datasets:
            node_data_files.append(self._create_node_data_files(dataset))

        for i in range(self.num_nodes):
            config = {
                "org_id": i + 1,
                "api_key": "TODO",
                "node_name": f"{self.server_name}-node-{i + 1}",
                "user_defined_config": extra_config,
            }
            config_file = self._create_node_config_file(
                config,
                [files[i] for files in node_data_files],
            )
            self.node_configs.append(config)
            self.node_config_files.append(config_file)

        info(
            f"Created {Fore.GREEN}{len(self.node_config_files)}{Style.RESET_ALL} node "
            f"configuration(s), attaching them to {Fore.GREEN}{self.server_name}"
            f"{Style.RESET_ALL}."
        )

    def _create_vserver_import_config(self) -> None:
        """Create server configuration import file (YAML)."""
        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )
        template = environment.get_template(SERVER_IMPORT_TEMPLATE_FILE)

        organizations = []
        collaboration = {"name": "demo", "participants": []}
        for config in self.node_configs:
            org_id = config["org_id"]
            org_data = {"name": f"org_{org_id}"}

            organizations.append(org_data)
            collaboration["participants"].append({"name": f"org_{org_id}"})
        organizations[0]["make_admin"] = True
        info(
            f"Organization {Fore.GREEN}{self.node_configs[0]['org_id']}"
            f"{Style.RESET_ALL} is the admin"
        )

        server_import_config = template.render(
            organizations=organizations, collaboration=collaboration
        )
        folders = ServerContext.instance_folders(
            InstanceType.SERVER, self.server_name, False
        )

        demo_dir = Path(folders["dev"])
        demo_dir.mkdir(parents=True, exist_ok=True)
        self.server_import_config_file = demo_dir / f"{self.server_name}.yaml"
        if self.server_import_config_file.exists():
            error(
                "Server configuration file already exists: "
                f"{self.server_import_config_file}"
            )
            exit(1)

        try:
            with open(self.server_import_config_file, "x") as f:
                f.write(server_import_config)
                info(
                    "Server import configuration ready, writing to "
                    f"{Fore.GREEN}{self.server_import_config_file}{Style.RESET_ALL}"
                )
        except Exception as e:
            error(f"Could not write server import configuration file: {e}")
            exit(1)

    def __server_config_return_func(self, extra_config: str, data_dir: Path) -> dict:
        """
        Return a dict with server configuration values to be used in creating the
        config file.

        Parameters
        ----------
        extra_config : str
            Extra configuration to be added to the server configuration.
        data_dir : Path
            Path to the data directory.

        Returns
        -------
        dict
            Dictionary with server configuration values.
        """
        return {
            "server": {
                "baseUrl": f"{LOCALHOST}:{self.server_port}",
                # TODO: v5+ set to latest v5 image
                # TODO make this configurable
                "image": (
                    self.server_image
                    or "harbor2.vantage6.ai/infrastructure/server:5.0.0a36"
                ),
                "algorithm_stores": [
                    {
                        "name": "local",
                        "url": f"{LOCALHOST}:{self.algorithm_store_port}",
                    }
                ],
                "logging": {},
                "keycloakUrl": f"http://vantage6-{self.server_name}-auth-user-auth-keycloak.{self.namespace}.svc.cluster.local",
                "additional_config": extra_config,
            },
            "rabbitmq": {},
            "database": {
                # TODO v5+ make configurable so that sandbox may work on WSL
                "volumePath": str(data_dir),
                "k8sNodeName": self.k8s_node_name,
            },
            "ui": {
                "port": self.ui_port,
                # TODO: v5+ set to latest v5 image
                # TODO: make this configurable
                "image": (
                    self.ui_image or "harbor2.vantage6.ai/infrastructure/ui:5.0.0a36"
                ),
            },
        }

    def _create_vserver_config(self) -> None:
        """Creates server configuration file (YAML)."""

        folders = ServerContext.instance_folders(
            instance_type=InstanceType.SERVER,
            instance_name=self.server_name,
            system_folders=False,
        )
        data_dir = Path(folders["dev"]) / self.server_name
        data_dir.mkdir(parents=True, exist_ok=True)

        extra_config = self._read_extra_config_file(self.extra_server_config)
        if self.ui_image is not None:
            if extra_config:
                extra_config += "\n"
            extra_config += f"images:\n  ui: {self.ui_image}"

        # Create the server config file
        self.server_config_file = new(
            config_producing_func=self.__server_config_return_func,
            config_producing_func_args=(extra_config, data_dir),
            name=self.server_name,
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.SERVER,
            is_sandbox=True,
        )

    def _create_algo_store_config(self) -> None:
        """Create algorithm store configuration file (YAML)."""

        extra_config = self._read_extra_config_file(self.extra_store_config)

        self.algo_store_config_file = new(
            config_producing_func=self.__algo_store_config_return_func,
            config_producing_func_args=(extra_config,),
            name=f"{self.server_name}-store",
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.ALGORITHM_STORE,
            is_sandbox=True,
        )

    def __algo_store_config_return_func(self, extra_config: str) -> dict:
        """
        Return a dict with algorithm store configuration values to be used in creating
        the config file.

        Returns
        -------
        dict
            Dictionary with algorithm store configuration values.
        """
        return {
            "store": {
                "internal": {
                    "port": self.algorithm_store_port,
                },
                "logging": {},
                "vantage6ServerUri": f"{LOCALHOST}:{self.server_port}",
                "additional_config": extra_config,
                "image": (
                    self.store_image
                    or "harbor2.vantage6.ai/infrastructure/store:5.0.0a36"
                ),
            },
            "database": {},
        }

    def _create_auth_config(self) -> None:
        """Create auth configuration file (YAML)."""
        self.auth_config_file = new(
            config_producing_func=self.__auth_config_return_func,
            config_producing_func_args=(),
            name=f"{self.server_name}-auth",
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.AUTH,
            is_sandbox=True,
        )

    def __auth_config_return_func(self) -> dict:
        """
        Return a dict with auth configuration values to be used in creating the
        config file.
        """

        return {
            "keycloak": {
                "production": False,
                "redirectUris": [
                    f"{LOCALHOST}:7600",
                    f"{LOCALHOST}:7681",
                ],
            },
        }


def wait_for_server_to_be_ready(server_port: int) -> None:
    """
    Wait for the server to be initialized.

    Parameters
    ----------
    server_port : int
        Port of the server.
    """
    client = Client(
        # TODO replace default API path global
        server_url=f"{LOCALHOST}:{server_port}/server",
        auth_url=f"{LOCALHOST}:{Ports.DEV_AUTH}",
        log_level=LogLevel.ERROR,
    )
    max_retries = 100
    wait_time = 3
    ready = False
    for _ in range(max_retries):
        try:
            result = client.util.get_server_health()
            if result and result.get("healthy"):
                info("Server is ready.")
                ready = True
                break
        except Exception:
            info("Waiting for server to be ready...")
            time.sleep(wait_time)

    if not ready:
        error("Server did not become ready in time. Exiting...")
        exit(1)


# TODO:
# - [ ] Accept the additional config files for the server, node and algorithm store
# - [ ] Exit gracefully when one of the steps fails
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
# TODO: I am missing the `--store-image` option, also --node-image
@click.option(
    "--server-image",
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
    "--store-image",
    type=str,
    default=None,
    help="Algorithm store docker image to use when setting up resources for "
    "the development algorithm store",
)
@click.option(
    "--node-image",
    type=str,
    default=None,
    help="Node docker image to use when setting up resources for the development node",
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
    default=None,
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file.",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--k8s-node-name", default="docker-desktop", help="Kubernetes node name to use"
)
@click.pass_context
def cli_new_sandbox(
    click_ctx: click.Context,
    name: str,
    num_nodes: int,
    server_port: int,
    ui_port: int,
    algorithm_store_port: int,
    server_image: str | None = None,
    ui_image: str | None = None,
    store_image: str | None = None,
    node_image: str | None = None,
    extra_server_config: Path | None = None,
    extra_node_config: Path | None = None,
    extra_store_config: Path | None = None,
    add_dataset: tuple[str, Path] | None = None,
    context: str | None = None,
    namespace: str | None = None,
    k8s_node_name: str = "docker-desktop",
) -> None:
    """
    Create a sandbox environment.
    """

    # Prompt for the k8s namespace and context
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    server_name = prompt_config_name(name)
    if ServerContext.config_exists(server_name, False, is_sandbox=True):
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} already exists!")
        exit(1)

    sb_config_manager = SandboxConfigManager(
        server_name=server_name,
        num_nodes=num_nodes,
        server_port=server_port,
        ui_port=ui_port,
        algorithm_store_port=algorithm_store_port,
        server_image=server_image,
        ui_image=ui_image,
        store_image=store_image,
        node_image=node_image,
        extra_server_config=extra_server_config,
        extra_node_config=extra_node_config,
        extra_store_config=extra_store_config,
        extra_dataset=add_dataset,
        context=context,
        namespace=namespace,
        k8s_node_name=k8s_node_name,
    )

    ctx = get_server_context(server_name, False, ServerContext, is_sandbox=True)

    # First we need to start the keycloak service
    info("Starting keycloak service")
    cmd = [
        "v6",
        "auth",
        "start",
        "--name",
        f"{server_name}-auth.sandbox",
        "--user",
        "--context",
        context,
        "--namespace",
        namespace,
        "--sandbox",
    ]
    subprocess.run(cmd, check=True)
    # Note: the CLI auth start function is blocking until the auth service is ready,
    # so no need to wait for it to be ready here.

    # Then we need to start the server
    info("Starting vantage6 server")
    click_ctx.invoke(
        cli_server_start,
        ctx=ctx,
        name=ctx.name,
        system_folders=False,
        namespace=namespace,
        context=context,
        attach=False,
    )
    wait_for_server_to_be_ready(server_port)

    raise

    # Then start the import process
    info("Starting import process")
    # TODO: The clients and users are not deleted. The server will fail the import if
    # they already exist.
    node_details_from_server = click_ctx.invoke(
        cli_server_import,
        ctx=ctx,
        file=sb_config_manager.server_import_config_file,
        drop_all=False,
    )

    print(node_details_from_server)

    info("Updating node configuration files with API keys")
    # TODO: @bart this is where I left off. I tried to update the config files with the
    # API keys, it should be something like this:
    # for idx, node_detail in enumerate(node_details_from_server):
    #     node_config_file = node_config_files[idx]
    #     cm = ConfigurationManager.from_file(node_config_files, is_sandbox=True)
    #     cm.config["node"]["api_key"] = node_detail["api_key"]
    #     cm.save(node_config_file)
    # Reply from Bart: I think we should do this in a very different way: we start up
    # the server and use the client to generate nodes. Only then should we create the
    # node config files. It makes sense to me to try to sync the scripts from the dev
    # env with the sandbox env, so that we don't need to maintain two processes.

    click_ctx.invoke(
        cli_server_stop,
        name=server_name,
        context=context,
        namespace=namespace,
        system_folders=False,
        all_servers=True,
        is_sandbox=True,
    )

    info("Sandbox environment was set up successfully!")
    info("Start it using the following command:")
    info(f"{Fore.GREEN}v6 sandbox start{Style.RESET_ALL}")

    # find user credentials to print. Read from server import file
    with open(sb_config_manager.server_import_config_file, "r") as f:
        server_import_config = yaml.safe_load(f)

    try:
        user = server_import_config["organizations"][0]["users"][0]
        username = user["username"]
        password = user["password"]
        info("You can login with the following credentials:")
        info(f"Username: {Fore.GREEN}{username}{Style.RESET_ALL}")
        info(f"Password: {Fore.GREEN}{password}{Style.RESET_ALL}")
    except KeyError:
        # No user found, skip printing credentials
        pass
