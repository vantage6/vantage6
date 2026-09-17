# Keep existing CLI imports working while the implementations used by the node
# and server live in vantage6-common.
from vantage6.common.configuration_manager import (
    Configuration,
    ConfigurationManager,
    LOGGING_VALIDATORS,
    NodeConfiguration,
    NodeConfigurationManager,
    ServerConfiguration,
    ServerConfigurationManager,
)

__all__ = [
    "Configuration",
    "ConfigurationManager",
    "LOGGING_VALIDATORS",
    "NodeConfiguration",
    "NodeConfigurationManager",
    "ServerConfiguration",
    "ServerConfigurationManager",
    "TestConfiguration",
    "TestingConfigurationManager",
]


class TestConfiguration(Configuration):
    VALIDATORS = {}


class TestingConfigurationManager(ConfigurationManager):
    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=TestConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=TestConfiguration)
