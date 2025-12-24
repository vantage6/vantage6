from __future__ import annotations

from vantage6.common.context import AppContext
from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli.configuration_manager import TestingConfigurationManager


class TestContext(AppContext):
    """
    Backend context for testing purposes.

    This context is used to test the backend applications, i.e. the HQ and the
    algorithm store.
    """

    INST_CONFIG_MANAGER = TestingConfigurationManager
    LOGGING_ENABLED = False

    @classmethod
    def from_external_config_file(
        cls, package_folder: str, instance_type: InstanceType
    ) -> TestContext:
        """
        Create a context the unittest configuration file.

        Returns
        -------
        TestContext
            Context object
        """
        return super().from_external_config_file(
            cls.test_config_location(package_folder, instance_type), instance_type, True
        )

    @staticmethod
    def test_config_location(package_folder: str, instance_type: InstanceType) -> str:
        """
        Location of the unittest configuration file.

        Returns
        -------
        str
            Path to the unittest configuration file
        """
        if instance_type == InstanceType.HQ:
            return package_folder / APPNAME / "hq" / "_data" / "unittest_config.yaml"
        elif instance_type == InstanceType.ALGORITHM_STORE:
            return (
                package_folder
                / APPNAME
                / "algorithm"
                / "store"
                / "_data"
                / "unittest_config.yaml"
            )
