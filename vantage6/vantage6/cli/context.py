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

import vantage6.cli.globals as constants


from vantage6.common.context import AppContext
from vantage6.cli.configuration_manager import (
    ConfigurationManager,
    ServerConfigurationManager,
    NodeConfigurationManager
)


class NodeContext(AppContext):
    """Node context on the host machine (used by the CLI). See 
    DockerNodeContext for the node instance mounts on the docker deamon"""
    
    INST_CONFIG_MANAGER = NodeConfigurationManager
    
    def __init__(self, instance_name, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        super().__init__("node", instance_name, environment=environment, 
            system_folders=system_folders)
    
    def get_database_uri(self, label="default"):
        return self.config["databases"][label]
    
    @property
    def databases(self):
        return self.config["databases"]

    @classmethod
    def from_external_config_file(cls, path, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        return super().from_external_config_file(
            path, "node", environment, system_folders
        )

    @classmethod
    def config_exists(cls, instance_name, environment=constants.DEFAULT_NODE_ENVIRONMENT, system_folders=False):
        return super().config_exists("node", 
            instance_name, environment=environment, system_folders=system_folders)
    
    @classmethod
    def available_configurations(cls, system_folders=constants.DEFAULT_NODE_SYSTEM_FOLDERS):
        return super().available_configurations("node", system_folders)

