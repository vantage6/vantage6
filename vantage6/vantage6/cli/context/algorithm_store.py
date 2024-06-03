from __future__ import annotations

from vantage6.common.globals import APPNAME, InstanceType
from vantage6.cli.configuration_manager import ServerConfigurationManager
from vantage6.cli.globals import (
    DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL,
    ServerType,
    AlgoStoreGlobals,
)
from vantage6.cli._version import __version__
from vantage6.cli.context.base_server import BaseServerContext


class AlgorithmStoreContext(BaseServerContext):
    """
    A context class for the algorithm store server.

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    system_folders : bool, optional
        System wide or user configuration, by default S_FOL
    """

    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name: str, system_folders: bool = S_FOL):
        super().__init__(
            InstanceType.ALGORITHM_STORE, instance_name, system_folders=system_folders
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
        return super().get_database_uri(AlgoStoreGlobals.DB_URI_ENV_VAR)

    @property
    def docker_container_name(self) -> str:
        """
        Name of the docker container that the server is running in.

        Returns
        -------
        str
            Server's docker container name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-{ServerType.ALGORITHM_STORE}"

    @classmethod
    def from_external_config_file(
        cls, path: str, system_folders: bool = S_FOL
    ) -> AlgorithmStoreContext:
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

        Returns
        -------
        AlgorithmStoreContext
            Server context object
        """
        return super().from_external_config_file(
            path,
            ServerType.ALGORITHM_STORE,
            AlgoStoreGlobals.CONFIG_NAME_ENV_VAR,
            system_folders,
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
            InstanceType.ALGORITHM_STORE, instance_name, system_folders
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
        return super().available_configurations(
            InstanceType.ALGORITHM_STORE, system_folders
        )
