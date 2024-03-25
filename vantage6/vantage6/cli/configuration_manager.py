from schema import And, Or, Use, Optional

from vantage6.common.configuration_manager import Configuration, ConfigurationManager

LOGGING_VALIDATORS = {
    "level": And(
        Use(str), lambda lvl: lvl in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
    ),
    "use_console": Use(bool),
    "backup_count": And(Use(int), lambda n: n > 0),
    "max_size": And(Use(int), lambda b: b > 16),
    "format": Use(str),
    "datefmt": Use(str),
}


class ServerConfiguration(Configuration):
    """
    Stores the server's configuration and defines a set of server-specific
    validators.
    """

    VALIDATORS = {
        "description": Use(str),
        "ip": Use(str),
        "port": Use(int),
        Optional("api_path"): str,
        "uri": Use(str),
        "allow_drop_all": Use(bool),
        "logging": {**LOGGING_VALIDATORS, "file": Use(str)},
        Optional("server_name"): str,
    }


class NodeConfiguration(Configuration):
    """
    Stores the node's configuration and defines a set of node-specific
    validators.
    """

    VALIDATORS = {
        "api_key": Use(str),
        "server_url": Use(str),
        "port": Or(Use(int), None),
        "task_dir": Use(str),
        # TODO: remove `dict` validation from databases
        "databases": Or([Use(dict)], dict, None),
        "api_path": Use(str),
        "logging": LOGGING_VALIDATORS,
        "encryption": {"enabled": bool, Optional("private_key"): Use(str)},
        Optional("node_extra_env"): dict,
        Optional("node_extra_mounts"): [str],
        Optional("node_extra_hosts"): dict,
    }


class TestConfiguration(Configuration):
    VALIDATORS = {}


class NodeConfigurationManager(ConfigurationManager):
    """
    Maintains the node's configuration.

    Parameters
    ----------
    name : str
        Name of the configuration file.
    """

    def __init__(self, name, *args, **kwargs) -> None:
        super().__init__(conf_class=NodeConfiguration, name=name)

    @classmethod
    def from_file(cls, path: str) -> "NodeConfigurationManager":
        """
        Create a new instance of the NodeConfigurationManager from a
        configuration file.

        Parameters
        ----------
        path : str
            Path to the configuration file.

        Returns
        -------
        NodeConfigurationManager
            A new instance of the NodeConfigurationManager.
        """
        return super().from_file(path, conf_class=NodeConfiguration)


class ServerConfigurationManager(ConfigurationManager):
    """
    Maintains the server's configuration.

    Parameters
    ----------
    name : str
        Name of the configuration file.
    """

    def __init__(self, name, *args, **kwargs) -> None:
        super().__init__(conf_class=ServerConfiguration, name=name)

    @classmethod
    def from_file(cls, path) -> "ServerConfigurationManager":
        """
        Create a new instance of the ServerConfigurationManager from a
        configuration file.

        Parameters
        ----------
        path : str
            Path to the configuration file.

        Returns
        -------
        ServerConfigurationManager
            A new instance of the ServerConfigurationManager.
        """
        return super().from_file(path, conf_class=ServerConfiguration)


class TestingConfigurationManager(ConfigurationManager):
    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=TestConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=TestConfiguration)
