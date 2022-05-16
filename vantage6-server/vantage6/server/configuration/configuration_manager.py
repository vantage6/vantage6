from schema import And, Use

from vantage6.common.configuration_manager import (
    Configuration,
    ConfigurationManager
)


class ServerConfiguration(Configuration):

    VALIDATORS = {
        "description": Use(str),
        "ip": Use(str),
        "port": Use(int),
        "api_path": Use(str),
        "uri": Use(str),
        "allow_drop_all": Use(bool),
        "logging": {
            "level": And(Use(str), lambda l: l in ("DEBUG", "INFO", "WARNING",
                                                   "ERROR", "CRITICAL")),
            "file": Use(str),
            "use_console": Use(bool),
            "backup_count": And(Use(int), lambda n: n > 0),
            "max_size": And(Use(int), lambda b: b > 16),
            "format": Use(str),
            "datefmt": Use(str)
        }
    }


class TestConfiguration(Configuration):
    VALIDATORS = {}


class ServerConfigurationManager(ConfigurationManager):

    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=ServerConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=ServerConfiguration)


class TestingConfigurationManager(ConfigurationManager):

    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=TestConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=TestConfiguration)
