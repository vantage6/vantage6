from __future__ import annotations

import collections
from abc import abstractmethod
from pathlib import Path
from typing import Any, Type

import yaml
from jinja2 import Environment, FileSystemLoader, Template
from schema import Schema, SchemaError

from vantage6.cli.globals import TEMPLATE_FOLDER


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
            self.VALIDATORS.get(key, lambda x: True), ignore_extra_keys=True
        )
        assert schema.is_valid(
            value
        ), f"Invalid value '{value}' provided for field '{key}'"
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
        is_valid = schema.is_valid(self.data)
        if not is_valid:
            try:
                schema.validate(self.data)
            except SchemaError as exc:
                raise SchemaError(f"Invalid configuration: {exc}") from exc
        return is_valid


class ConfigurationManager(object):
    """Class to maintain valid configuration settings.

    Parameters
    ----------
    conf_class: Configuration
        The class to use for the configuration.
    name: str
        The name of the configuration.
    """

    def __init__(
        self, conf_class: Configuration = Configuration, name: str = None
    ) -> None:
        self.config = {}

        self.name = name
        self.conf_class = conf_class

    def put(self, config: dict) -> None:
        """
        Add a configuration to the configuration manager.

        Parameters
        ----------
        config: dict
            The configuration to add.

        Raises
        ------
        AssertionError
            If the configuration is not valid.
        """
        configuration = self.conf_class(config)
        if configuration.is_valid:
            self.config = config

    def get(self) -> Configuration:
        """
        Get a configuration from the configuration manager.

        Returns
        -------
        Configuration
            The configuration.
        """
        return self.config

    @property
    def is_empty(self) -> bool:
        """
        Check if the configuration manager is empty.

        Returns
        -------
        bool
            Whether or not the configuration manager is empty.
        """
        return not self.config

    def load(self, path: Path | str) -> None:
        """
        Load a configuration from a file.

        Parameters
        ----------
        path: Path | str
            The path to the file to load the configuration from.
        """
        with open(str(path), "r") as f:
            config = yaml.safe_load(f)

        self.put(config)

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
        assert name, f"Configuration name could not be extracted from filepath={path}"
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
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        template = self.get_config_template()
        rendered_config = template.render(self.config)
        with open(path, "x", encoding="utf-8") as f:
            f.write(rendered_config)

    @abstractmethod
    def get_config_template(self) -> Template:
        """
        Get the configuration template for the server.
        """
        pass

    @classmethod
    def _get_config_template(cls, template_file: str) -> Template:
        """
        Get the configuration template for the server.

        Parameters
        ----------
        template_file: str
            The name of the template file to get.

        Returns
        -------
        jinja2.Template
            The configuration template.
        """
        environment = Environment(
            loader=FileSystemLoader(TEMPLATE_FOLDER),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )
        return environment.get_template(template_file)
