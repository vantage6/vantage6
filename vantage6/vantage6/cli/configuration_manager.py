from schema import And, Or, Use, Optional

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


class NodeConfiguration(Configuration):

    VALIDATORS = {
        "api_key": Use(str),
        "server_url": Use(str),
        "port": Or(Use(int), None),
        "task_dir": Use(str),
        "databases": {Use(str): Use(str)},
        "api_path": Use(str),
        "logging": {
            "level": And(Use(str), lambda l: l in ("DEBUG", "INFO", "WARNING",
                                                   "ERROR", "CRITICAL")),
            "file": Use(str),
            "use_console": Use(bool),
            "backup_count": And(Use(int), lambda n: n > 0),
            "max_size": And(Use(int), lambda b: b > 16),
            "format": Use(str),
            "datefmt": Use(str)
        },
        "encryption": {
            "enabled": bool,
            Optional("private_key"): Use(str)
        }
    }


class NodeConfigurationManager(ConfigurationManager):

    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=NodeConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=NodeConfiguration)


class ServerConfigurationManager(ConfigurationManager):

    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=ServerConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=ServerConfiguration)
