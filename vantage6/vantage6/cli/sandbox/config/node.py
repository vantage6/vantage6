from dataclasses import dataclass
from importlib import resources as impresources
from pathlib import Path

import pandas as pd
from colorama import Fore, Style

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

import vantage6.cli.sandbox.data as node_datafiles_dir
from vantage6.cli.common.new import new
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import (
    DefaultDatasets,
)
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.sandbox.config.base import BaseSandboxConfigManager
from vantage6.cli.sandbox.populate.helpers.utils import (
    path_to_str,
    replace_wsl_path,
    str_replace_wsl_path,
)


@dataclass
class NodeDataset:
    label: str
    path: Path


class NodeSandboxConfigManager(BaseSandboxConfigManager):
    """
    Class to store the node sandbox configurations.

    Parameters
    ----------
    server_name : str
        Name of the server.
    api_keys : list[str]
        List of API keys.
    node_names : list[str]
        List of node names.
    server_port : int
        Port of the server.
    node_image : str | None
        Image of the node.
    extra_node_config : Path | None
        Path to the extra node configuration file.
    extra_dataset : NodeDataset | None
        List of tuples with the label and path to the dataset file.
    k8s_config : KubernetesConfig
        Kubernetes configuration.
    custom_data_dir : Path | None
        Path to the custom data directory. Useful on WSL because of mount issues for
        default directories.
    with_prometheus : bool
        Whether Prometheus is enabled for the node.
    """

    def __init__(
        self,
        server_name: str,
        api_keys: list[str],
        node_names: list[str],
        server_port: int,
        node_image: str | None,
        extra_node_config: Path | None,
        extra_dataset: NodeDataset | None,
        k8s_config: KubernetesConfig,
        custom_data_dir: Path | None,
        with_prometheus: bool = False,
    ) -> None:
        super().__init__(server_name, custom_data_dir)
        self.api_keys = api_keys
        self.node_names = node_names
        self.num_nodes = len(api_keys)
        self.server_port = server_port
        self.node_image = node_image
        self.extra_node_config = extra_node_config
        if extra_dataset:
            self.node_datasets = [extra_dataset]
        else:
            self.node_datasets = []
        self.k8s_config = k8s_config
        self.with_prometheus = with_prometheus

        self.node_configs = []
        self.node_config_files = []
        self.node_config_names = []
        self.extra_config = None

    def generate_node_configs(self) -> None:
        """
        Generates ``num_nodes`` node configuration files.
        """
        node_data_files = []
        self.extra_config = self._read_extra_config_file(self.extra_node_config)

        data_directory = impresources.files(node_datafiles_dir)

        # Add default datasets to the list of dataset provided
        for default_dataset in DefaultDatasets:
            # note that the label is the name of the dataset with the underscores
            # replace with hyphens, to make it valid for k8s
            self.node_datasets.append(
                NodeDataset(
                    label=default_dataset.name.lower().replace("_", "-"),
                    path=data_directory / default_dataset.value,
                )
            )

        # Check for duplicate dataset labels
        seen_labels = set()
        duplicates = [
            label
            for label in [dataset.label for dataset in self.node_datasets]
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

        for idx, api_key in enumerate(self.api_keys):
            config = {
                "org_id": idx + 1,
                "api_key": api_key,
                "node_name": self.node_names[idx],
            }
            config_file = self._create_node_config_file(
                config,
                [files[idx] for files in node_data_files],
            )
            self.node_configs.append(config)
            self.node_config_files.append(config_file)
        info(
            f"Created {Fore.GREEN}{len(self.node_config_files)}{Style.RESET_ALL} node "
            f"configuration(s), attaching them to {Fore.GREEN}{self.server_name}"
            f"{Style.RESET_ALL}."
        )

    def _create_node_data_files(
        self, node_dataset: NodeDataset
    ) -> list[tuple[str, Path]]:
        """
        Create data files for nodes.

        Parameters
        ----------
        node_dataset : NodeDataset
            Tuple with the label and path to the dataset file.

        Returns
        -------
        list[tuple[str, Path]]
            List of tuples with the label and path to the dataset file.
        """
        info(
            f"Creating data files using dataset '{node_dataset.label}' for "
            f"{self.num_nodes} nodes"
        )
        data_files = []
        full_df = pd.read_csv(node_dataset.path)
        length_df = len(full_df)
        for i in range(self.num_nodes):
            node_name = f"{self.server_name}_node_{i + 1}"
            path_to_dev_dir = self._create_and_get_data_dir(
                InstanceType.NODE, is_data_folder=False
            )

            # Split the data over the nodes
            start = i * length_df // self.num_nodes
            end = (i + 1) * length_df // self.num_nodes
            data = full_df[start:end]
            data_file = (
                replace_wsl_path(Path(path_to_dev_dir), to_mnt_wsl=True)
                / f"df_{node_dataset.label}_{node_name}.csv"
            )

            # write data to file
            data.to_csv(data_file, index=False)
            data_files.append(
                (node_dataset.label, str_replace_wsl_path(data_file, to_mnt_wsl=False))
            )
        return data_files

    def _create_node_config_file(
        self, config: dict, datasets: list[tuple[str, Path]]
    ) -> Path:
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
        config_name = f"{self.server_name}-{node_name}"

        path_to_data_dir = self._create_and_get_data_dir(
            InstanceType.NODE, is_data_folder=True, node_name=node_name
        )
        log_dir = self._create_and_get_data_dir(
            InstanceType.NODE, is_log_dir=True, node_name=node_name
        )

        # delete old node config if it exists
        NodeContext.remove_config_file_if_exists(
            InstanceType.NODE, config_name, False, is_sandbox=True
        )

        # create new node config
        node_config = new(
            config_producing_func=self.__node_config_return_func,
            config_producing_func_args=(
                config,
                self.extra_config,
                datasets,
                path_to_data_dir,
                log_dir,
            ),
            name=config_name,
            system_folders=False,
            type_=InstanceType.NODE,
            is_sandbox=True,
        )

        self.node_config_names.append(config_name)

        return node_config

    def __node_config_return_func(
        self,
        node_specific_config: dict,
        extra_config: dict,
        datasets: list[tuple[str, Path]],
        path_to_data_dir: Path,
        log_dir: Path,
    ) -> dict:
        """
        Return a dict with node configuration values to be used in creating the
        config file.
        """
        config = {
            "node": {
                "proxyPort": 7676 + int(node_specific_config["org_id"]),
                "apiKey": node_specific_config["api_key"],
                "name": node_specific_config["node_name"],
                "logging": {
                    "level": "DEBUG",
                    "file": f"{node_specific_config['node_name']}.log",
                    "volumeHostPath": str(log_dir),
                },
                "keycloakUrl": (
                    f"http://vantage6-{self.server_name}-auth-user-auth-keycloak."
                    f"{self.k8s_config.namespace}.svc.cluster.local"
                ),
                "persistence": {
                    "tasks": {
                        "hostPath": str(path_to_data_dir),
                        "size": "1Gi",
                    },
                    "database": {
                        "size": "1Gi",
                    },
                },
                "k8sNodeName": self.k8s_config.k8s_node,
                "databases": {
                    "fileBased": [
                        {
                            "name": dataset[0],
                            "uri": dataset[1],
                            "type": "csv",
                            # Call path_to_str to ensure that the path is a Linux-style string path.
                            # This is relevant for Windows paths in the sandbox environment.
                            "volumePath": path_to_str(Path(dataset[1]).parent),
                            "originalName": Path(dataset[1]).name,
                        }
                        for dataset in [datasets[0]]
                    ]
                },
                "server": {
                    "url": (
                        f"http://vantage6-{self.server_name}-user-server-vantage6-"
                        f"server-service.{self.k8s_config.namespace}.svc.cluster"
                        ".local"
                    ),
                    "port": self.server_port,
                },
            },
        }
        if self.node_image:
            config["node"]["image"] = self.node_image

        if self.with_prometheus:
            config["node"]["prometheus"] = {
                "enabled": True,
                "report_interval_seconds": 45,
            }

        # merge the extra config with the node config
        if extra_config is not None:
            config.update(extra_config)

        return config
