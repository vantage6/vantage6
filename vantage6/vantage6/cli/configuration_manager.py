from typing import Self

from schema import And, Optional, Or, Use

from vantage6.common.configuration_manager import Configuration, ConfigurationManager

from vantage6.cli.globals import ALGO_STORE_TEMPLATE_FILE, SERVER_TEMPLATE_FILE

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

    # TODO: explore how to validate helm values.yaml files, see issue 2105
    VALIDATORS = {}


class AlgorithmStoreConfiguration(Configuration):
    """
    Stores the algorithm store's configuration and defines a set of algorithm store-specific
    validators.
    """

    VALIDATORS = {}


class NodeConfiguration(Configuration):
    """
    Stores the node's configuration and defines a set of node-specific
    validators.
    """

    VALIDATORS = {
        "server_url": Use(str),
        "port": Or(Use(int), None),
        "task_dir": Use(str),
        # TODO: remove `dict` validation from databases
        "api_path": Use(str),
        "logging": LOGGING_VALIDATORS,
        "encryption": {"enabled": bool, Optional("private_key"): Use(str)},
        Optional("node_extra_env"): dict,
        Optional("node_extra_mounts"): [str],
        Optional("node_extra_hosts"): dict,
        Optional("share_algorithm_logs"): Use(bool),
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
    def from_file(cls, path: str) -> Self:
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
    def from_file(cls, path) -> Self:
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

    def get_config_template(self) -> str:
        """
        Get the configuration template for the server.

        Returns
        -------
        str
            The configuration template for the server.
        """
        return super()._get_config_template(SERVER_TEMPLATE_FILE)


class AlgorithmStoreConfigurationManager(ConfigurationManager):
    """
    Maintains the algorithm store's configuration.

    Parameters
    ----------
    name : str
        Name of the configuration file.
    """

    def __init__(self, name, *args, **kwargs) -> None:
        super().__init__(conf_class=AlgorithmStoreConfiguration, name=name)

    @classmethod
    def from_file(cls, path: str) -> Self:
        """
        Create a new instance of the AlgorithmStoreConfigurationManager from a
        configuration file.

        Parameters
        ----------
        path : str
            Path to the configuration file.

        Returns
        -------
        AlgorithmStoreConfigurationManager
            A new instance of the AlgorithmStoreConfigurationManager.
        """
        return super().from_file(path, conf_class=AlgorithmStoreConfiguration)

    def get_config_template(self) -> str:
        """
        Get the configuration template for the algorithm store.

        Returns
        -------
        str
            The configuration template for the algorithm store.
        """
        return super()._get_config_template(ALGO_STORE_TEMPLATE_FILE)


class TestingConfigurationManager(ConfigurationManager):
    def __init__(self, name, *args, **kwargs):
        super().__init__(conf_class=TestConfiguration, name=name)

    @classmethod
    def from_file(cls, path):
        return super().from_file(path, conf_class=TestConfiguration)
