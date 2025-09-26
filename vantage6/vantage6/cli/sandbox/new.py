from importlib import resources as impresources
from pathlib import Path

import click
import pandas as pd
import yaml
from colorama import Fore, Style
from jinja2 import Environment, FileSystemLoader

from vantage6.common import ensure_config_dir_writable, error, info
from vantage6.common.globals import APPNAME, InstanceType, Ports

import vantage6.cli.sandbox.data as node_datafiles_dir
from vantage6.cli.common.new import new
from vantage6.cli.common.utils import select_context_and_namespace
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.context.node import NodeContext
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import (
    ALGO_STORE_TEMPLATE_FILE,
    NODE_TEMPLATE_FILE,
    PACKAGE_FOLDER,
    SERVER_IMPORT_TEMPLATE_FILE,
    DefaultDatasets,
)
from vantage6.cli.server.common import get_server_context
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.utils import prompt_config_name


class SandboxConfigManager:
    """
    Class to store the sandbox configurations.
    """

    def __init__(
        self,
        server_name: str,
        num_nodes: int,
        server_url: str,
        server_port: int,
        ui_port: int,
        algorithm_store_port: int,
        image: str,
        ui_image: str,
        extra_server_config: Path,
        extra_node_config: Path,
        extra_store_config: Path,
        add_dataset: list[tuple[str, Path]],
        context: str,
        namespace: str,
    ):
        self.server_name = server_name
        self.num_nodes = num_nodes
        self.server_url = server_url
        self.server_port = server_port
        self.ui_port = ui_port
        self.algorithm_store_port = algorithm_store_port
        self.image = image
        self.ui_image = ui_image
        self.extra_server_config = extra_server_config
        self.extra_node_config = extra_node_config
        self.extra_store_config = extra_store_config
        self.add_dataset = add_dataset
        self.context = context
        self.namespace = namespace

        self.node_configs = []
        self.node_config_files = []
        self.server_import_config_file = None
        self.server_config_file = None
        self.store_config_file = None

        self._initialize_configs()

    def _initialize_configs(self) -> None:
        """Generates the demo network."""
        self._generate_node_configs()

        self._create_vserver_import_config()

        self._create_vserver_config()

        self._create_algo_store_config()

    def _create_node_data_files(self) -> None:
        """Create data files for nodes."""
        info(f"Creating data files for {self.num_nodes} nodes.")
        data_files = []
        full_df = pd.read_csv(self.add_dataset[1])
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
            data_file = data_folder / f"df_{self.add_dataset[0]}_{node_name}.csv"

            # write data to file
            data.to_csv(data_file, index=False)
            data_files.append((self.add_dataset[0], data_file))
        return data_files

    def _create_node_config_file(
        self, config: dict, datasets: list[tuple[str, Path]] | None = None
    ) -> None:
        """Create a node configuration file (YAML)."""
        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )
        template = environment.get_template(NODE_TEMPLATE_FILE)

        # TODO: make this name specific to the server it connects
        node_name = config["node_name"]
        folders = NodeContext.instance_folders("node", node_name, False)
        path_to_dev_dir = Path(folders["dev"] / self.server_name)
        path_to_dev_dir.mkdir(parents=True, exist_ok=True)

        path_to_data_dir = Path(folders["data"])
        path_to_data_dir.mkdir(parents=True, exist_ok=True)
        full_path = Path(folders["config"] / f"{node_name}.sandbox.yaml")

        if full_path.exists():
            error(f"Node configuration file already exists: {full_path}")
            exit(1)

        if datasets is None:
            datasets = []

        node_config = template.render(
            {
                "node": {
                    "proxyPort": 7676 + int(config["org_id"]),
                    "api_key": config["api_key"],
                    "image": "harbor2.vantage6.ai/infrastructure/node:frank",
                    "logging": {"file": f"{node_name}.log", "loggers": []},
                    # TODO: the keycloak instance should be spun up together with the
                    # server
                    "keycloakUrl": (
                        "http://vantage6-auth-keycloak.default.svc.cluster.local"
                    ),
                    "keycloakRealm": "vantage6",
                    "additional_config": config["user_defined_config"],
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
                        "url": self.server_url,
                        "port": self.server_port,
                    },
                },
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
            f"Created node configuration file for organization {Fore.GREEN}"
            f"{config['org_id']}{Style.RESET_ALL}"
        )

        return Path(full_path)

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
        """Generates ``num_nodes`` node configuration files."""
        node_data_files = []
        extra_config = self._read_extra_config_file(self.extra_node_config)

        data_directory = impresources.files(node_datafiles_dir)

        # Add default datasets to the list of dataset provided
        for default_dataset in DefaultDatasets:
            self.add_dataset.append(
                (
                    default_dataset.name.lower().replace("_", "-"),
                    data_directory / default_dataset.value,
                )
            )

        # Check for duplicate dataset labels
        seen_labels = set()
        duplicates = [
            label
            for label in [dataset[0] for dataset in self.add_dataset]
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
        for dataset in self.add_dataset:
            node_data_files.append(
                self._create_node_data_files(self.num_nodes, self.server_name, dataset)
            )

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
                f"Server configuration file already exists: {self.server_import_config_file}"
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
        """
        return {
            "server": {
                "baseUrl": f"{self.server_url}:{self.server_port}",
                # TODO: v5+ set to latest v5 image
                # TODO make this configurable
                "image": "harbor2.vantage6.ai/infrastructure/server:5.0.0a36",
                "algorithm_stores": [
                    {
                        "name": "local",
                        "url": f"{self.server_url}:{self.algorithm_store_port}",
                    }
                ],
                "logging": {},
                "keycloakUrl": "http://vantage6-auth-keycloak.default.svc.cluster.local",
                "additional_config": extra_config,
            },
            "rabbitmq": {},
            "database": {
                "volumePath": str(data_dir),
                "k8sNodeName": "docker-desktop",
            },
            "ui": {
                "port": self.ui_port,
                # TODO: v5+ set to latest v5 image
                # TODO: make this configurable
                "image": "harbor2.vantage6.ai/infrastructure/ui:5.0.0a36",
            },
        }

    def _create_vserver_config(self) -> None:
        """Creates server configuration file (YAML)."""

        folders = ServerContext.instance_folders(
            instance_type=InstanceType.SERVER,
            instance_name=self.server_name,
            system_folders=False,
        )
        data_dir = Path(folders["dev"])
        data_dir.mkdir(parents=True, exist_ok=True)

        extra_config = self._read_extra_config_file(self.extra_server_config)
        if self.ui_image is not None:
            if extra_config:
                extra_config += "\n"
            extra_config += f"images:\n  ui: {self.ui_image}"

        # Create the server config file
        new(
            config_producing_func=self.__server_config_return_func,
            name=self.server_name,
            system_folders=False,
            namespace=self.namespace,
            context=self.context,
            type_=InstanceType.SERVER,
            is_sandbox=True,
        )

    def _create_algo_store_config(self) -> None:
        """Create algorithm store configuration file (YAML)."""
        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )

        extra_config = self._read_extra_config_file(self.extra_store_config)

        template = environment.get_template(ALGO_STORE_TEMPLATE_FILE)
        store_config = template.render(
            {
                "store": {
                    "internal": {
                        "port": self.algorithm_store_port,
                    },
                    "logging": {},
                    "vantage6ServerUri": f"{self.server_url}:{self.server_port}",
                    "additional_config": extra_config,
                },
                "database": {},
            }
        )
        folders = AlgorithmStoreContext.instance_folders(
            instance_type=InstanceType.ALGORITHM_STORE,
            instance_name=f"{self.server_name}_store",
            system_folders=False,
        )

        config_dir = Path(folders["config"] / f"{self.server_name}_store")
        config_dir.mkdir(parents=True, exist_ok=True)
        self.algo_store_config_file = (
            folders["config"] / f"{self.server_name}_store.yaml"
        )
        if self.algo_store_config_file.exists():
            error(
                f"Algorithm store configuration file already exists: "
                f"{self.algo_store_config_file}"
            )
            exit(1)

        try:
            with open(self.algo_store_config_file, "x") as f:
                f.write(store_config)
                info(
                    "Algorithm store configuration ready, writing to "
                    f"{Fore.GREEN}{self.algo_store_config_file}{Style.RESET_ALL}"
                )
        except Exception as e:
            error(f"Could not write algorithm store configuration file: {e}")
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
# TODO I think we can remove this option as it should be the same for all?
@click.option(
    "--server-url",
    type=str,
    default="http://localhost",
    help="Server URL to point to. If you are using the default setup using Docker "
    "Desktop, the default http://localhost should not be changed.",
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
# TODO: this should be `--server-image`
# TODO: I am missing the `--store-image` option
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
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.pass_context
def cli_new_sandbox(
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
    context: str = None,
    namespace: str = None,
) -> dict:
    """
    Create a sandbox environment.
    """
    server_name = prompt_config_name(name)
    if not ServerContext.config_exists(server_name, False, is_sandbox=True):
        sb_config_manager = SandboxConfigManager(
            server_name,
            num_nodes,
            server_url,
            server_port,
            ui_port,
            algorithm_store_port,
            image,
            ui_image,
            extra_server_config,
            extra_node_config,
            extra_store_config,
            add_dataset,
            context,
            namespace,
        )
    else:
        error(f"Configuration {Fore.RED}{server_name}{Style.RESET_ALL} already exists!")
        exit(1)

    ctx = get_server_context(server_name, False, ServerContext, is_sandbox=True)

    # Prompt for the k8s namespace and context
    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    # First we need to start the server, store and auth
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

    # Wait a moment for the server to be fully ready
    import time

    time.sleep(5)

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
