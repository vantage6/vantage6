from __future__ import annotations

import hashlib
import os.path
from pathlib import Path

from vantage6.common.context import AppContext
from vantage6.common.globals import APPNAME, STRING_ENCODING, InstanceType

from vantage6.cli import __version__
from vantage6.cli.configuration_manager import NodeConfigurationManager
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL


class NodeContext(AppContext):
    """
    Node context object for the host system.

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    system_folders : bool, optional
        _description_, by default N_FOL
    config_file : str, optional
        _description_, by default None
    in_container : bool, optional
        Whether the application is running inside a container, by default False
    """

    # The server configuration manager is aware of the structure of the server
    # configuration file and makes sure only valid configuration can be loaded.
    INST_CONFIG_MANAGER = NodeConfigurationManager

    def __init__(
        self,
        instance_name: str,
        system_folders: bool = N_FOL,
        config_file: str = None,
        print_log_header: bool = True,
        logger_prefix: str = "",
        in_container: bool = False,
    ):
        super().__init__(
            InstanceType.NODE,
            instance_name,
            system_folders=system_folders,
            config_file=config_file,
            print_log_header=print_log_header,
            logger_prefix=logger_prefix,
            in_container=in_container,
        )
        if print_log_header:
            self.log.info("vantage6 version '%s'", __version__)
        self.identifier = self.__create_node_identifier()

    @classmethod
    def from_external_config_file(
        cls, path: str, system_folders: bool = N_FOL
    ) -> NodeContext:
        """
        Create a node context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        NodeContext
            Node context object
        """
        return super().from_external_config_file(
            Path(path).resolve(), InstanceType.NODE, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name: str, system_folders: bool = N_FOL) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().config_exists(
            InstanceType.NODE, instance_name, system_folders=system_folders
        )

    @classmethod
    def available_configurations(
        cls, system_folders: bool = N_FOL
    ) -> tuple[list, list]:
        """
        Find all available server configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        tuple[list, list]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations(InstanceType.NODE, system_folders)

    @staticmethod
    def type_data_folder(system_folders: bool = N_FOL) -> Path:
        """
        Obtain OS specific data folder where to store node specific data.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration

        Returns
        -------
        Path
            Path to the data folder
        """
        return AppContext.type_data_folder(InstanceType.NODE, system_folders)

    @property
    def databases(self) -> dict:
        """
        Dictionary of local databases that are available for this node.

        Returns
        -------
        dict
            dictionary with database names as keys and their corresponding
            paths as values.
        """
        return self.config["databases"]

    @property
    def docker_container_name(self) -> str:
        """
        Docker container name of the node.

        Returns
        -------
        str
            Node's Docker container name
        """
        return f"{APPNAME}-{self.name}-{self.scope}"

    @property
    def docker_network_name(self) -> str:
        """
        Private Docker network name which is unique for this node.

        Returns
        -------
        str
            Docker network name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-net"

    @property
    def docker_volume_name(self) -> str:
        """
        Docker volume in which task data is stored. In case a file based
        database is used, this volume contains the database file as well.

        Returns
        -------
        str
            Docker volume name
        """
        return os.environ.get("DATA_VOLUME_NAME", f"{self.docker_container_name}-vol")

    @property
    def proxy_log_file(self):
        return self.log_file_name(type_="proxy_server")

    def get_database_uri(self, label: str = "default") -> str:
        """
        Obtain the database URI for a specific database.

        Parameters
        ----------
        label : str, optional
            Database label, by default "default"

        Returns
        -------
        str
            URI to the database
        """
        return self.config["databases"][label]

    def set_folders(
        self, instance_type: InstanceType, instance_name: str, system_folders: bool
    ) -> None:
        """
        Set the folders for the node.

        Parameters
        ----------
        instance_type : InstanceType
            Instance type
        instance_name : str
            Instance name
        system_folders : bool
            Whether to use system folders
        """
        dirs = self.instance_folders(instance_type, instance_name, system_folders)

        self.log_dir = dirs.get("log")
        self.data_dir = dirs.get("data")
        self.config_dir = dirs.get("config")

    @staticmethod
    def instance_folders(*_args, **_kwargs) -> dict:
        """Log, data and config folders are always mounted. The node manager
        should take care of this.
        """
        mnt = Path("/mnt")

        return {
            "log": mnt / "log",
            "data": mnt / "data",
            "config": mnt / "config",
        }

    def __create_node_identifier(self) -> str:
        """
        Create a unique identifier for the node.

        Returns
        -------
        str
            Unique identifier for the node
        """
        return hashlib.sha256(
            os.environ.get("V6_API_KEY").encode(STRING_ENCODING)
        ).hexdigest()[:16]
