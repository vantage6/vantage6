import os.path

from sqlalchemy.engine.url import make_url

import vantage6.cli.globals as constants
from vantage6.cli.configuration_manager import (NodeConfigurationManager,
                                                ServerConfigurationManager)
from vantage6.common.context import AppContext
from vantage6.common.globals import APPNAME


class ServerContext(AppContext):
    """ Context for the server.

        Overwrites some methods from the AppContext. Also keeps track
        of where the database is located.
    """

    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name,
                 environment=constants.DEFAULT_SERVER_ENVIRONMENT,
                 system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):

        super().__init__("server", instance_name, environment=environment,
                         system_folders=system_folders)

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
    def from_external_config_file(
        cls, path,
        environment=constants.DEFAULT_SERVER_ENVIRONMENT,
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS
    ):

        return super().from_external_config_file(
            path, "server", environment, system_folders
        )

    @classmethod
    def config_exists(
        cls, instance_name,
        environment=constants.DEFAULT_SERVER_ENVIRONMENT,
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS
    ):

        return super().config_exists("server", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(
        cls,
        system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS
    ):

        return super().available_configurations("server", system_folders)

class NodeContext(AppContext):
    """ Context for the node.

        Context for the node when it is run on the host machine. The
        Context for the Dockerized version is NodeDockerContext.
    """

    INST_CONFIG_MANAGER = NodeConfigurationManager

    def __init__(self, instance_name,
                 environment=constants.DEFAULT_NODE_ENVIRONMENT,
                 system_folders=False):

        super().__init__("node", instance_name, environment=environment,
                         system_folders=system_folders)

    def get_database_uri(self, label="default"):
        return self.config["databases"][label]

    @property
    def databases(self):
        return self.config["databases"]

    @classmethod
    def from_external_config_file(
        cls, path, environment=constants.DEFAULT_NODE_ENVIRONMENT,
        system_folders=False
    ):
        return super().from_external_config_file(
            path, "node", environment, system_folders
        )

    @classmethod
    def config_exists(
        cls, instance_name,
        environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False
    ):
        return super().config_exists("node", instance_name,
                                     environment=environment,
                                     system_folders=system_folders)

    @classmethod
    def available_configurations(
        cls, system_folders=constants.DEFAULT_NODE_SYSTEM_FOLDERS
    ):
        return super().available_configurations("node", system_folders)
