from __future__ import annotations
import vantage6.server.globals as constants

from vantage6.common.context import AppContext
from vantage6.cli.configuration_manager import TestingConfigurationManager


class TestContext(AppContext):
    """
    Server context for testing purposes.

    Note that this context is specific to the server: for nodes, there is a
    separate test context.
    """

    INST_CONFIG_MANAGER = TestingConfigurationManager
    LOGGING_ENABLED = False

    @classmethod
    def from_external_config_file(cls) -> TestContext:
        """
        Create a context the unittest configuration file.

        Returns
        -------
        TestContext
            Context object
        """
        return super().from_external_config_file(
            cls.test_config_location(), "unittest", True
        )

    @staticmethod
    def test_config_location() -> str:
        """
        Location of the unittest configuration file.

        Returns
        -------
        str
            Path to the unittest configuration file
        """
        return (
            constants.PACKAGE_FOLDER
            / constants.APPNAME
            / "server"
            / "_data"
            / "unittest_config.yaml"
        )
