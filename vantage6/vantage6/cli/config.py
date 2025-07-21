import os
from os import PathLike
from pathlib import Path

import questionary
import yaml
from colorama import Fore, Style
from kubernetes import config

from vantage6.common import info, warning

from vantage6.cli.globals import (
    DEFAULT_CLI_CONFIG_FILE,
)


class CliConfig:
    """
    A class to manage CLI configuration for Kubernetes context and namespace.

    The CLI configuration is stored in a `config.yaml` file located at the path
    specified by `DEFAULT_CLI_CONFIG_FILE`.

    The `config.yaml` file has the following structure:

    ```yaml
    kube:
      last_context: <last_used_k8s_context>
      last_namespace: <last_used_k8s_namespace>
    ```

    Attributes
    ----------
    config_path : PathLike
        Path to the configuration file.
    _cached_config : dict or None
        Cached configuration data.
    _cached_mtime : float or None
        Last modification time of the configuration file.
    """

    def __init__(self, config_path: str | PathLike = DEFAULT_CLI_CONFIG_FILE) -> None:
        """
        Initialize the CliConfig object.

        Parameters
        ----------
        config_path : str or PathLike, optional
            Path to the configuration file.
        """
        self.config_path: PathLike = Path(config_path)
        self._cached_config: dict | None = None
        self._cached_mtime: float | None = None

    def _load_config(self) -> dict:
        """
        Load the configuration from the file.

        Returns
        -------
        dict
            The loaded configuration data.
        """
        if self.config_path.exists():
            with open(self.config_path, "r") as config_file:
                return yaml.safe_load(config_file) or {}
        return {}

    def _save_config(self, config: dict) -> None:
        """
        Save the configuration to the file.

        Parameters
        ----------
        config : dict
            The configuration data to save.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as config_file:
            yaml.dump(config, config_file)

    def _reload_cache_lazy(self) -> None:
        """
        Reload the configuration cache if the file has been modified.
        """
        if self.config_path.exists():
            mtime = os.path.getmtime(self.config_path)
            if self._cached_mtime != mtime:
                self._cached_config = self._load_config()
                self._cached_mtime = mtime
        else:
            self._cached_config = {}
            self._cached_mtime = None

    def get_last_context(self) -> str | None:
        """
        Get the last used Kubernetes context.

        Returns
        -------
        str or None
            The last used Kubernetes context, or None if not set.
        """
        self._reload_cache_lazy()
        return self._cached_config.get("kube", {}).get("last_context")

    def set_last_context(self, context: str) -> None:
        """
        Set the Kubernetes context.

        Parameters
        ----------
        context : str
            The Kubernetes context to set.
        """
        config = self._load_config()
        if "kube" not in config:
            config["kube"] = {}

        if config["kube"].get("last_context") != context:
            config["kube"]["last_context"] = context
            self._save_config(config)
            self._reload_cache_lazy()

    def get_last_namespace(self) -> str | None:
        """
        Get the last used Kubernetes namespace.

        Returns
        -------
        str or None
            The last used Kubernetes namespace, or None if not set.
        """
        self._reload_cache_lazy()
        return self._cached_config.get("kube", {}).get("last_namespace")

    def set_last_namespace(self, namespace: str) -> None:
        """
        Set the Kubernetes namespace.

        Parameters
        ----------
        namespace : str
            The Kubernetes namespace to set.
        """
        config = self._load_config()
        if "kube" not in config:
            config["kube"] = {}

        if config["kube"].get("last_namespace") != namespace:
            config["kube"]["last_namespace"] = namespace
            self._save_config(config)
            self._reload_cache_lazy()

    def remove_kube(self) -> None:
        """
        Remove the last used context and namespace.
        """
        if self.config_path.exists():
            config = self._load_config()
            if "kube" in config:
                del config["kube"]
                self._save_config(config)
                self._reload_cache_lazy()

    def get_active_settings(
        self,
        context: str | None,
        namespace: str | None,
    ) -> tuple[str, str]:
        """
        Get the active Kubernetes context and namespace.

        Parameters
        ----------
        context : str or None
            The Kubernetes context to use.
        namespace : str or None
            The Kubernetes namespace to use.

        Returns
        -------
        tuple[str, str]
            A tuple containing the active context and namespace.
        """
        if not context:
            _, active_context = config.list_kube_config_contexts()
            context = active_context["name"]

        if not namespace:
            namespace = active_context["context"].get("namespace", "default")

        return context, namespace

    def compare_changes_config(
        self,
        context: str | None = None,
        namespace: str | None = None,
    ) -> tuple[str, str]:
        """
        Compare active settings with last used settings.

        Parameters
        ----------
        context : str or None, optional
            The Kubernetes context to use.
        namespace : str or None, optional
            The Kubernetes namespace to use.

        Returns
        -------
        tuple[str, str]
            A tuple containing the active context and namespace.
        """

        active_context, active_namespace = self.get_active_settings(context, namespace)
        last_context = self.get_last_context()
        last_namespace = self.get_last_namespace()

        # compare context
        if not last_context:
            self.set_last_context(context=active_context)
        elif last_context != active_context:
            warning("Are you using the correct context?")
            warning(f"Current context: {Fore.YELLOW}{active_context}{Style.RESET_ALL}")
            warning(f"Last    context: {Fore.YELLOW}{last_context}{Style.RESET_ALL}")

            active_context = questionary.select(
                "Which context do you want to use?",
                choices=[active_context, last_context],
                default=active_context,
            ).ask()

            if last_context != active_context:
                self.set_last_context(context=active_context)

        # compare namespace
        if not last_namespace:
            self.set_last_namespace(namespace=active_namespace)
        elif last_namespace != active_namespace:
            warning("Are you using the correct namespace?")
            warning(
                f"Current namespace: {Fore.YELLOW}{active_namespace}{Style.RESET_ALL}"
            )
            warning(
                f"Last    namespace: {Fore.YELLOW}{last_namespace}{Style.RESET_ALL}"
            )

            active_namespace = questionary.select(
                "Which namespace do you want to use?",
                choices=[active_namespace, last_namespace],
                default=active_namespace,
            ).ask()

            if last_namespace != active_namespace:
                self.set_last_namespace(namespace=active_namespace)

        info(f"Using    context: {Fore.YELLOW}{active_context}{Style.RESET_ALL}")
        info(f"Using  namespace: {Fore.YELLOW}{active_namespace}{Style.RESET_ALL}")
        return active_context, active_namespace
