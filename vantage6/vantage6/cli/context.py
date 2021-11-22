import os.path

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
    """ Context for the server.

        Overwrites some methods from the AppContext. Also keeps track
        of where the database is located.
    """

    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name, environment=S_ENV, system_folders=S_FOL):
        super().__init__("server", instance_name, environment=environment,
                         system_folders=system_folders)
        self.log.info(f"vantage6 version '{__version__}'")

    def get_database_uri(self):
        """ In the Docker environment we would like to overwrite the
            uri setting by an environment variable.
        """
        uri = os.environ.get("VANTAGE6_DB_URI") or self.config['uri']
        URL = make_url(uri)

        if (URL.host is None) and (not os.path.isabs(URL.database)):
            # We're dealing with a relative path here.
            URL.database = str(self.data_dir / URL.database)
            uri = str(URL)

        return uri

    @property
    def docker_container_name(self):
        return f"{APPNAME}-{self.name}-{self.scope}-server"

    @classmethod
    def from_external_config_file(cls, path, environment=S_ENV,
                                  system_folders=S_FOL):
        return super().from_external_config_file(
            path, "server", environment, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name, environment=S_ENV,
                      system_folders=S_FOL):
        return super().config_exists("server", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(cls, system_folders=S_FOL):
        return super().available_configurations("server", system_folders)


class NodeContext(AppContext):
    """Node context on the host machine (used by the CLI).

    See DockerNodeContext for the node instance mounts when running as a
    dockerized service.
    """

    # FIXME: drop the prefix "INST_": a *class* is assigned.
    # FIXME: this does not need to be a class attribute, but ~~can~~_should_
    #        be set in __init__
    INST_CONFIG_MANAGER = NodeConfigurationManager

    running_in_docker = False

    def __init__(self, instance_name, environment=N_ENV,
                 system_folders=N_FOL, config_file=None):
        super().__init__("node", instance_name, environment, system_folders,
                         config_file)
        self.log.info(f"vantage6 version '{__version__}'")

    @classmethod
    def from_external_config_file(cls, path, environment=N_ENV,
                                  system_folders=N_FOL):
        return super().from_external_config_file(path, "node", environment,
                                                 system_folders)

    @classmethod
    def config_exists(cls, instance_name, environment=N_ENV,
                      system_folders=N_FOL):
        return super().config_exists("node", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(cls, system_folders=N_FOL):
        return super().available_configurations("node", system_folders)

    @staticmethod
    def type_data_folder(system_folders):
        """Return OS specific data folder."""
        return AppContext.type_data_folder("node", system_folders)

    @property
    def databases(self):
        return self.config["databases"]

    @property
    def docker_container_name(self):
        return f"{APPNAME}-{self.name}-{self.scope}"

    @property
    def docker_network_name(self):
        return f"{APPNAME}-{self.name}-{self.scope}-net"

    @property
    def docker_volume_name(self):
        return os.environ.get(
            'DATA_VOLUME_NAME',
            f"{self.docker_container_name}-vol"
        )

    @property
    def docker_vpn_volume_name(self):
        return os.environ.get(
            'VPN_VOLUME_NAME',
            f"{self.docker_container_name}-vpn-vol"
        )

    def docker_temporary_volume_name(self, run_id):
        return f"{APPNAME}-{self.name}-{self.scope}-{run_id}-tmpvol"

    def get_database_uri(self, label="default"):
        return self.config["databases"][label]
