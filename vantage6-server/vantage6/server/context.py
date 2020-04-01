import os
import sys
import appdirs
import logging
import logging.handlers

from pathlib import Path
from sqlalchemy.engine.url import make_url

import vantage6.server.globals as constants

from vantage6.common import Singleton
from vantage6.common.context import AppContext
from vantage6.server.configuration.configuration_manager import (
    ConfigurationManager,
    ServerConfigurationManager,
    TestingConfigurationManager
)


class ServerContext(AppContext):

    INST_CONFIG_MANAGER = ServerConfigurationManager

    def __init__(self, instance_name,
                 environment=constants.DEFAULT_SERVER_ENVIRONMENT,
                 system_folders=constants.DEFAULT_SERVER_SYSTEM_FOLDERS):

        super().__init__("server", instance_name, environment=environment,
                         system_folders=system_folders)

    def get_database_uri(self):
        uri = self.config['uri']
        URL = make_url(uri)

        if (URL.host is None) and (not os.path.isabs(URL.database)):
            # We're dealing with a relative path here.
            URL.database = str(self.data_dir / URL.database)
            uri = str(URL)

        return uri

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
            "server" / "_data" / "unittest_config.yaml")

    @staticmethod
    def test_data_location():
        return ( constants.PACAKAGE_FOLDER / constants.APPNAME / \
            "server" / "_data" )