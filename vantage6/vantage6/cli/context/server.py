from __future__ import annotations

from pathlib import Path

from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli import __version__
from vantage6.cli.configuration_manager import ServerConfigurationManager
from vantage6.cli.context.base_server import BaseServerContext
from vantage6.cli.globals import (
    DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL,
    PROMETHEUS_DIR,
    ServerType,
)


class ServerContext(BaseServerContext):
    """
    Server context

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    system_folders : bool, optional
        System wide or user configuration, by default S_FOL
    """

    # The server configuration manager is aware of the structure of the server
    # configuration file and makes sure only valid configuration can be loaded.
    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(
        self,
        instance_name: str,
        system_folders: bool = S_FOL,
        in_container: bool = False,
    ):
        super().__init__(
            InstanceType.SERVER,
            instance_name,
            system_folders=system_folders,
            in_container=in_container,
        )
        self.log.info("vantage6 version '%s'", __version__)

    def get_database_uri(self) -> str:
        """
        Obtain the database uri from the environment or the configuration.

        Returns
        -------
        str
            string representation of the database uri
        """
        return super().get_database_uri()

    @property
    def docker_container_name(self) -> str:
        """
        Name of the docker container that the server is running in.

        Returns
        -------
        str
            Server's docker container name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-{ServerType.V6SERVER.value}"

    @property
    def prometheus_container_name(self) -> str:
        """
        Get the name of the Prometheus Docker container for this server.

        Returns
        -------
        str
            Prometheus container name, unique to this server instance.
        """
        return f"{APPNAME}-{self.name}-{self.scope}-prometheus"

    @property
    def prometheus_dir(self) -> Path:
        """
        Get the Prometheus directory path.

        Returns
        -------
        Path
            Path to the Prometheus directory
        """
        return self.data_dir / PROMETHEUS_DIR

    @classmethod
    def from_external_config_file(
        cls, path: str, system_folders: bool = S_FOL, in_container: bool = False
    ) -> ServerContext:
        """
        Create a server context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL
        in_container : bool, optional
            Whether the application is running inside a container, by default False

        Returns
        -------
        ServerContext
            Server context object
        """
        return super().from_external_config_file(
            path,
            ServerType.V6SERVER,
            system_folders,
            in_container,
        )

    @classmethod
    def config_exists(cls, instance_name: str, system_folders: bool = S_FOL) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().config_exists(
            InstanceType.SERVER, instance_name, system_folders=system_folders
        )

    @classmethod
    def available_configurations(
        cls, system_folders: bool = S_FOL
    ) -> tuple[list, list]:
        """
        Find all available server configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        tuple[list, list]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations(InstanceType.SERVER, system_folders)
