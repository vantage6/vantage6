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

from vantage6.common.globals import (
    PACAKAGE_FOLDER,
    APPNAME
)
from vantage6.common.context import AppContext
from vantage6.common.configuration_manager import ConfigurationManager
from vantage6.cli.context import NodeContext
from vantage6.node import __version__


class DockerNodeContext(NodeContext):
    """Node context for the dockerized version of the node."""

    running_in_docker = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log.info(f"Node package version '{__version__}'")

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


class TestingConfigurationManager(ConfigurationManager):
    VALIDATORS = {}



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
        return ( PACAKAGE_FOLDER / APPNAME / \
            "_data" / "unittest_config.yaml")

    @staticmethod
    def test_data_location():
        return ( PACAKAGE_FOLDER / APPNAME / \
            "_data" )