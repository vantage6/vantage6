from __future__ import annotations

import os.path
from pathlib import Path

from sqlalchemy.engine.url import make_url

from vantage6.common._version import __version__
from vantage6.common.configuration_manager import ServerConfigurationManager
from vantage6.common.context import AppContext
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL,
    InstanceType,
)

PROMETHEUS_DIR = "prometheus"
SERVER_DB_URI_ENV_VAR = "VANTAGE6_DB_URI"
SERVER_CONFIG_NAME_ENV_VAR = "VANTAGE6_CONFIG_NAME"


class BaseServerContext(AppContext):
    """
    Base context for a vantage6 server or algorithm store server

    Contains functions that the ServerContext and AlgorithmStoreContext have
    in common.
    """

    def get_database_uri(self, db_env_var: str) -> str:
        """
        Obtain the database uri from the environment or the configuration.

        Parameters
        ----------
        db_env_var : str
            Name of the environment variable that contains the database uri

        Returns
        -------
        str
            string representation of the database uri
        """
        uri = os.environ.get(db_env_var) or self.config["uri"]
        url = make_url(uri)

        if url.host is None and not os.path.isabs(url.database):
            # We're dealing with a relative path here of a local database, when
            # we're running the server outside of docker. Therefore we need to
            # prepend the data directory to the database name, but after the
            # driver name (e.g. sqlite:////db.sqlite ->
            # sqlite:////data_dir>/db.sqlite)

            # find index of database name
            idx_db_name = str(url).find(url.database)

            # add the datadir to the right location in the database uri
            return str(url)[:idx_db_name] + str(self.data_dir / url.database)

        return uri

    @classmethod
    def from_external_config_file(
        cls,
        path: str,
        server_type: str,
        config_name_env_var: str,
        system_folders: bool = S_FOL,
    ) -> BaseServerContext:
        """
        Create a server context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        server_type : str
            Type of server, either 'server' or 'algorithm-store'
        config_name_env_var : str
            Name of the environment variable that contains the name of the
            configuration
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        ServerContext
            Server context object
        """
        cls = super().from_external_config_file(path, server_type, system_folders)
        # if we are running a server in a docker container, the name is taken
        # from the name of the config file (which is usually a default). Get
        # the config name from environment if it is given.
        cls.name = os.environ.get(config_name_env_var) or cls.name
        return cls


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

    def __init__(self, instance_name: str, system_folders: bool = S_FOL):
        super().__init__(
            InstanceType.SERVER, instance_name, system_folders=system_folders
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
        return super().get_database_uri(SERVER_DB_URI_ENV_VAR)

    @property
    def docker_container_name(self) -> str:
        """
        Name of the docker container that the server is running in.

        Returns
        -------
        str
            Server's docker container name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-{InstanceType.SERVER.value}"

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
        cls, path: str, system_folders: bool = S_FOL
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

        Returns
        -------
        ServerContext
            Server context object
        """
        return super().from_external_config_file(
            path,
            InstanceType.SERVER,
            SERVER_CONFIG_NAME_ENV_VAR,
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
