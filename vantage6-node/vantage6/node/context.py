from pathlib import Path

from vantage6.common.globals import PACKAGE_FOLDER, APPNAME

from vantage6.common.context import AppContext
from vantage6.common.configuration_manager import ConfigurationManager
from vantage6.cli.context.node import NodeContext
from vantage6.node._version import __version__


class TestingConfigurationManager(ConfigurationManager):
    VALIDATORS = {}


class TestContext(AppContext):
    INST_CONFIG_MANAGER = TestingConfigurationManager
    LOGGING_ENABLED = False

    @classmethod
    def from_external_config_file(cls, path):
        return super().from_external_config_file(
            cls.test_config_location(), "unittest", True
        )

    @staticmethod
    def test_config_location():
        return PACKAGE_FOLDER / APPNAME / "_data" / "unittest_config.yaml"

    @staticmethod
    def test_data_location():
        return PACKAGE_FOLDER / APPNAME / "_data"
