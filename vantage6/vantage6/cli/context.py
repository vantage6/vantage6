import sys
import os, os.path
import logging
import logging.handlers
import appdirs
import yaml
import base64

from schema import SchemaError
from pathlib import Path
from sqlalchemy.engine.url import make_url

from vantage6.common.context import AppContext
from vantage6.common.globals import APPNAME

from vantage6.cli.globals import (
    DEFAULT_NODE_ENVIRONMENT as ENVIRONMENT,
    DEFAULT_NODE_SYSTEM_FOLDERS as SYSTEM_FOLDERS,
)

from vantage6.cli.configuration_manager import (
    ConfigurationManager,
    ServerConfigurationManager,
    NodeConfigurationManager
)


class NodeContext(AppContext):
    """Node context on the host machine (used by the CLI).

    See DockerNodeContext for the node instance mounts when running as a
    dockerized service.
    """

    # FIXME: drop the prefix "INST_": a *class* is assigned.
    # FIXME: this does not need to be a class attribute, but ~~can~~_should_
    #        be set in __init__
    INST_CONFIG_MANAGER = NodeConfigurationManager

    def __init__(self, instance_name, environment=ENVIRONMENT,
        system_folders=False, config_file=None):
        super().__init__("node", instance_name, environment, system_folders, config_file)

    @classmethod
    def from_external_config_file(cls, path, environment=ENVIRONMENT, system_folders=False):
        return super().from_external_config_file(
            path, "node", environment, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name, environment=ENVIRONMENT, system_folders=False):
        return super().config_exists("node",
            instance_name, environment=environment, system_folders=system_folders)

    @classmethod
    def available_configurations(cls, system_folders=SYSTEM_FOLDERS):
        return super().available_configurations("node", system_folders)

    @property
    def databases(self):
        return self.config["databases"]

    @property
    def docker_container_name(self):
        return f"{APPNAME}-{self.name}-{self.scope}"

    @property
    def docker_network_name(self):
        return f"{APPNAME}-{self.name}-{self.scope}"

    @property
    def docker_volume_name(self):
        return os.environ.get(
            'DATA_VOLUME_NAME',
            f"{self.docker_container_name}-vol"
        )

    def docker_temporary_volume_name(self, run_id):
        return f"{APPNAME}-{self.name}-{self.scope}-{run_id}-tmpvol"

    def get_database_uri(self, label="default"):
        return self.config["databases"][label]


