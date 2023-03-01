"""
The context module in the CLI package contains the definition of the
ServerContext and NodeContext classes. These contexts are related to the host
system and therefore part of the CLI package.

Both classes are derived from the abstract AppContext class. And provide the
node and server with naming conventions, standard file locations, and in the
case of the node with a local database URIs.

*Server Context*
    A class to provide context for the server, both for development mode as
    for production.

*Node Context*
    In case the node is run in development mode, this context will also used by
    the node package. Normally the node uses the
    `vantage6.node.context.DockerNodeContext` which provides the same
    functionality but is tailored to the Docker environment.
-------------------------------------------------------------------------------
"""
# TODO BvB 2023-01-10 we should have a look at all context classes and define
# them in the same place. Now the DockerNodeContext is defined in the node, but
# the server only has a TestServerContext there. This should be made consistent
from __future__ import annotations

import os.path

from typing import Tuple
from pathlib import Path

from sqlalchemy.engine.url import make_url

from vantage6.common.context import AppContext
from vantage6.common.globals import APPNAME
from vantage6.cli.configuration_manager import (NodeConfigurationManager,
                                                ServerConfigurationManager)
from vantage6.cli.globals import (DEFAULT_NODE_ENVIRONMENT as N_ENV,
                                  DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL,
                                  DEFAULT_SERVER_ENVIRONMENT as S_ENV,
                                  DEFAULT_SERVER_SYSTEM_FOLDERS as S_FOL)
from vantage6.cli._version import __version__


class ServerContext(AppContext):
    """
    Server context

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    environment : str, optional
        DTAP environment to load from the configuration file, by default
        S_ENV
    system_folders : bool, optional
        System wide or user configuration, by default S_FOL
    """

    # The server configuration manager is aware of the structure of the server
    # configuration file and makes sure only valid configuration can be loaded.
    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name: str, environment: str = S_ENV,
                 system_folders: bool = S_FOL):
        super().__init__("server", instance_name, environment=environment,
                         system_folders=system_folders)
        self.log.info(f"vantage6 version '{__version__}'")

    def get_database_uri(self) -> str:
        """
        Obtain the database uri from the environment or the configuration. The
        `VANTAGE6_DB_URI` environment variable is used by the Docker container,
        but can also be set by the user.

        Returns
        -------
        str
            string representation of the database uri
        """
        uri = os.environ.get("VANTAGE6_DB_URI") or self.config['uri']
        url = make_url(uri)

        if (url.host is None) and (not os.path.isabs(url.database)):
            # We're dealing with a relative path here.
            url.database = str(self.data_dir / url.database)
            uri = str(url)

        return uri

    @property
    def docker_container_name(self) -> str:
        """
        Unique name of the docker container.

        Returns
        -------
        str
            Unique docker container name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-server"

    @classmethod
    def from_external_config_file(
            cls, path: str, environment: str = S_ENV,
            system_folders: bool = S_FOL) -> ServerContext:
        """
        Create a server context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        environment : str, optional
            DTAP environment to be loaded, by default S_ENV
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        ServerContext
            Server context object
        """
        cls = super().from_external_config_file(
            path, "server", environment, system_folders
        )
        # if we are running a server in a docker container, the name is taken
        # from the name of the config file (which is usually a default). Get
        # the config name from environment if it is given.
        cls.name = os.environ.get("VANTAGE6_CONFIG_NAME") or cls.name
        return cls

    @classmethod
    def config_exists(cls, instance_name: str, environment: str = S_ENV,
                      system_folders: bool = S_FOL) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        environment : str, optional
            DTAP environment that needs to be present, by default S_ENV
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().config_exists("server", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(cls, system_folders: bool = S_FOL) \
            -> Tuple[list, list]:
        """
        Find all available server configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default S_FOL

        Returns
        -------
        Tuple[List, List]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations("server", system_folders)


class NodeContext(AppContext):
    """
    Node context

    See DockerNodeContext for the node instance mounts when running as a
    dockerized service.

    Parameters
    ----------
    instance_name : str
        Name of the configuration instance, corresponds to the filename
        of the configuration file.
    environment : str, optional
        DTAP environment to be loaded, by default N_ENV
    system_folders : bool, optional
        _description_, by default N_FOL
    config_file : str, optional
        _description_, by default None
    """

    # The server configuration manager is aware of the structure of the server
    # configuration file and makes sure only valid configuration can be loaded.
    INST_CONFIG_MANAGER = NodeConfigurationManager

    # Flag to indicate if the node is running in a docker container or directly
    # on the host machine.
    running_in_docker = False

    def __init__(self, instance_name: str, environment: str = N_ENV,
                 system_folders: bool = N_FOL, config_file: str = None):
        super().__init__("node", instance_name, environment, system_folders,
                         config_file)
        self.log.info(f"vantage6 version '{__version__}'")

    @classmethod
    def from_external_config_file(cls, path: str, environment: str = N_ENV,
                                  system_folders: bool = N_FOL) -> NodeContext:
        """
        Create a node context from an external configuration file. External
        means that the configuration file is not located in the default folders
        but its location is specified by the user.

        Parameters
        ----------
        path : str
            Path of the configuration file
        environment : str, optional
            DTAP environment to be loaded, by default N_ENV
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        NodeContext
            Node context object
        """
        return super().from_external_config_file(path, "node", environment,
                                                 system_folders)

    @classmethod
    def config_exists(cls, instance_name: str, environment: str = N_ENV,
                      system_folders: bool = N_FOL) -> bool:
        """
        Check if a configuration file exists.

        Parameters
        ----------
        instance_name : str
            Name of the configuration instance, corresponds to the filename
            of the configuration file.
        environment : str, optional
            DTAP environment that needs to be present, by default N_ENV
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        bool
            Whether the configuration file exists or not
        """
        return super().config_exists("node", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(cls, system_folders: bool = N_FOL) \
            -> Tuple[list, list]:
        """
        Find all available server configurations in the default folders.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        Tuple[List, List]
            The first list contains validated configuration files, the second
            list contains invalid configuration files.
        """
        return super().available_configurations("node", system_folders)

    @staticmethod
    def type_data_folder(system_folders: bool = N_FOL) -> Path:
        """
        Obtain OS specific data folder where to store node specific data.

        Parameters
        ----------
        system_folders : bool, optional
            System wide or user configuration, by default N_FOL

        Returns
        -------
        Path
            Path to the data folder
        """
        return AppContext.type_data_folder("node", system_folders)

    @property
    def databases(self):
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
        Unique Docker container name of the node.

        Returns
        -------
        str
            Unique Docker container name
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
        return os.environ.get(
            'DATA_VOLUME_NAME',
            f"{self.docker_container_name}-vol"
        )

    @property
    def docker_vpn_volume_name(self) -> str:
        """
        Docker volume in which the VPN configuration is stored.

        Returns
        -------
        str
            Docker volume name
        """
        return os.environ.get(
            'VPN_VOLUME_NAME',
            f"{self.docker_container_name}-vpn-vol"
        )

    @property
    def docker_ssh_volume_name(self) -> str:
        """
        Docker volume in which the SSH configuration is stored.

        Returns
        -------
        str
            Docker voluem name
        """
        return os.environ.get(
            'SSH_TUNNEL_VOLUME_NAME',
            f"{self.docker_container_name}-ssh-vol"
        )

    def docker_temporary_volume_name(self, run_id: int) -> str:
        """
        Docker volume in which temporary data is stored. Temporary data is
        linked to a specific run. Multiple algorithm containers can have the
        same run id, and therefore the share same temporary volume.

        Parameters
        ----------
        run_id : int
            run id provided by the server

        Returns
        -------
        str
            Docker volume name
        """
        return f"{APPNAME}-{self.name}-{self.scope}-{run_id}-tmpvol"

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
