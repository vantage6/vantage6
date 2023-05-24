from __future__ import annotations
import yaml
import collections

from typing import Any, Type
from pathlib import Path
from schema import Schema


class Configuration(collections.UserDict):
    """Base class to contain a single configuration."""

    VALIDATORS = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Validation of a single item when put

        Parameters
        ----------
        key: str
            The key of the item to set.
        value: Any
            The value of the item to set.

        Raises
        ------
        AssertionError
            If the value is not valid.
        """
        # assert key in self.VALIDATORS.keys(), "Invalid Key!"
        schema = Schema(
            self.VALIDATORS.get(key, lambda x: True),
            ignore_extra_keys=True
        )
        assert schema.is_valid(value), \
            f"Invalid value '{value}' provided for field '{key}'"
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> Any:
        """
        Get an item from the configuration.

        Parameters
        ----------
        key: str
            The key of the item to get.

        Returns
        -------
        Any
            The value of the item.

        Raises
        ------
        KeyError
            If the key is not in the configuration.
        """
        if key in self.data:
            return super().__getitem__(key)
        else:
            raise KeyError(key)

    @property
    def is_valid(self) -> bool:
        """
        Check if the configuration is valid.

        Returns
        -------
        bool
            Whether or not the configuration is valid.
        """
        schema = Schema(self.VALIDATORS, ignore_extra_keys=True)
        return schema.is_valid(self.data)


class ConfigurationManager(object):
    """Class to maintain valid configuration settings.

    A configuration file contains at top level an `application` and/or
    `environments` key. The `environments` key can contain up to four
    keys: `dev`, `test`, `acc`, `prod`. e.g.:

    application:
        ...
    environments:
        dev:
            ...
        test:
            ...
        acc:
            ...
        prod:
            ...

    Note that this structure is the same for the node and server.

    Parameters
    ----------
    conf_class: Configuration
        The class to use for the configuration.
    name: str
        The name of the configuration.
    """
    ENVS = ("application", "prod", "acc", "test", "dev")

    def __init__(self, conf_class: Configuration = Configuration,
                 name: str = None) -> None:
        self.application = ""
        self.prod = ""
        self.acc = ""
        self.test = ""
        self.dev = ""

        self.name = name
        self.conf_class = conf_class

    def put(self, env: str, config: dict) -> None:
        """
        Add a configuration to the configuration manager.

        Parameters
        ----------
        env: str
            The environment to add the configuration to.
        config: dict
            The configuration to add.

        Raises
        ------
        AssertionError
            If the environment is not valid.
        """
        assert env in self.ENVS
        configuration = self.conf_class(config)
        # only set valid configs
        if configuration.is_valid:
            self.__setattr__(env, configuration)
        # else:
        #      print(f"config={config}")
        #      print(self.conf_class)

    def get(self, env: str) -> Configuration:
        """
        Get a configuration from the configuration manager.

        Parameters
        ----------
        env: str
            The environment to get the configuration from.

        Returns
        -------
        Configuration
            The configuration.

        Raises
        ------
        AssertionError
            If the environment is not valid.
        """
        assert env in self.ENVS
        return self.__getattribute__(env)

    @property
    def is_empty(self) -> bool:
        """
        Check if the configuration manager is empty.

        Returns
        -------
        bool
            Whether or not the configuration manager is empty.
        """
        return not (self.application or self.prod or self.acc
                    or self.test or self.dev)

    @property
    def environments(self) -> dict:
        """
        Get all environments.

        Returns
        -------
        dict
            A dictionary containing all environments.
        """
        return {"prod": self.prod, "acc": self.acc, "test": self.test,
                "dev": self.dev, "application": self.application}

    @property
    def has_application(self) -> bool:
        """
        Check if the configuration manager has an application configuration.

        Returns
        -------
        bool
            Whether or not the configuration manager has an application
            configuration.
        """
        return bool(self.application)

    @property
    def has_environments(self) -> bool:
        """
        Check if the configuration manager has any environment configurations.

        Returns
        -------
        bool
            Whether or not the configuration manager has any environment
            configurations.
        """
        return any([bool(env) for key, env in self.environments])

    @property
    def available_environments(self) -> list[str]:
        """
        Get a list of available environments.

        Returns
        -------
        list[str]
            A list of available environments.
        """
        return [key for key, env in self.environments.items() if env]

    def _get_environment_from_dict(self, dic: dict, env: str) -> dict:
        """
        Get a configuration from a dictionary.

        Parameters
        ----------
        dic: dict
            The dictionary to get the configuration from.
        env: str
            The environment to get the configuration from.

        Returns
        -------
        dict
            The configuration.

        Raises
        ------
        AssertionError
            If the environment is not valid.
        """
        assert env in self.ENVS
        if env == "application":
            return dic.get("application", {})
        else:
            return dic.get("environments", {}).get(env, {})

    def load(self, path: Path | str) -> None:
        """
        Load a configuration from a file.

        Parameters
        ----------
        path: Path | str
            The path to the file to load the configuration from.
        """
        with open(str(path), 'r') as f:
            config = yaml.safe_load(f)

        for env in self.ENVS:
            self.put(env, self._get_environment_from_dict(config, env))

    @classmethod
    def from_file(
        cls, path: Path | str, conf_class: Type[Configuration] = Configuration
    ) -> ConfigurationManager:
        """
        Load a configuration from a file.

        Parameters
        ----------
        path: Path | str
            The path to the file to load the configuration from.
        conf_class: Type[Configuration]
            The class to use for the configuration.

        Returns
        -------
        ConfigurationManager
            The configuration manager with the configuration.

        Raises
        ------
        AssertionError
            If the name of the configuration could not be extracted from the
            file path.
        """
        name = Path(path).stem
        assert name, ("Configuration name could not be extracted from "
                      f"filepath={path}")
        conf = cls(name=name, conf_class=conf_class)
        conf.load(path)
        return conf

    def save(self, path: Path | str) -> None:
        """
        Save the configuration to a file.

        Parameters
        ----------
        path: Path | str
            The path to the file to save the configuration to.
        """
        config = {"application": dict(self.application), "environments": {
            "prod": dict(self.prod),
            "acc": dict(self.acc),
            "test": dict(self.test),
            "dev": dict(self.dev)}
        }

        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
