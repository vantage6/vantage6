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

import vantage6.node.globals as constants

from vantage6.common.context import AppContext
from vantage6.node.configuration.configuration_manager import (
    ConfigurationManager,
    ServerConfigurationManager,
    NodeConfigurationManager,
    TestingConfigurationManager
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

class DockerNodeContext(NodeContext):
    """Node context for the dockerized version of the node."""

    @staticmethod
    def instance_folders(instance_type, instance_name, system_folders):
        """Log, data and config folders are allways mounted mounted. The
        node manager should take care of this. """
        
        mnt = Path("/mnt")

        return {
            "log": mnt / "log",
            "data": mnt / "data",
            "config": mnt / "config"
        }



class TestContext(AppContext):

    INST_CONFIG_MANAGER = TestingConfigurationManager
    LOGGING_ENABLED = False
    
    @classmethod
    def from_external_config_file(cls, path):
        return super().from_external_config_file(
            cls.test_config_location(), 
            "unittest", "application", True
        )

    @staticmethod
    def test_config_location():
        return ( constants.PACAKAGE_FOLDER / constants.APPNAME / \
            "_data" / "unittest_config.yaml")

    @staticmethod
    def test_data_location():
        return ( constants.PACAKAGE_FOLDER / constants.APPNAME / \
            "_data" )