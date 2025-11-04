import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import appdirs
import questionary
import yaml
from colorama import Fore, Style
from kubernetes import config as k8s_config

from vantage6.common import info, warning
from vantage6.common.enum import StrEnumBase
from vantage6.common.globals import APPNAME

from vantage6.cli.globals import DEFAULT_CLI_CONFIG_FILE

_CONTEXT_INFO_PRINTED = False


class K8SConfigVariable(StrEnumBase):
    """
    Enum containing the variables of the Kubernetes configuration.
    """

    CONTEXT = "context"
    NAMESPACE = "namespace"


@dataclass
class KubernetesConfig:
    """
    Class to store Kubernetes configuration.

    Attributes
    ----------
    last_context : str or None
        The last used Kubernetes context.
    last_namespace : str or None
        The last used Kubernetes namespace.
    """

    last_context: str | None = None
    last_namespace: str | None = None

    def to_dict(self) -> dict:
        """
        Convert the Kubernetes configuration to a dictionary.
        """
        output = {}
        if self.last_context:
            output["last_context"] = self.last_context
        if self.last_namespace:
            output["last_namespace"] = self.last_namespace
        return output


class K8SConfigManager:
    """
    A class to manage CLI configuration for Kubernetes.

    The Kubernetes CLI configuration is stored in a YAML file, and contains, for
    example, the last used context and namespace.

    Attributes
    ----------
    config_path : PathLike
        Path to the configuration file.
    kubernetes_config : KubernetesConfig
        The Kubernetes configuration.
    _cached_mtime : float or None
        Last modification time of the configuration file.
    """

    def __init__(self) -> None:
        """
        Initialize the K8SConfigManager object.

        Parameters
        ----------
        config_path : str or PathLike, optional
            Path to the configuration file.
        """
        dirs = appdirs.AppDirs(APPNAME)
        self.config_path = Path(dirs.user_config_dir) / DEFAULT_CLI_CONFIG_FILE
        self._cached_mtime: float | None = None
        self.kubernetes_config = KubernetesConfig()

    def _load_config(self) -> None:
        """
        Load the configuration from the file.
        """
        loaded_config = {}
        if self.config_path.exists():
            with open(self.config_path, "r") as config_file:
                loaded_config = yaml.safe_load(config_file)

        context = loaded_config.get("last_context")
        namespace = loaded_config.get("last_namespace")
        self.kubernetes_config = KubernetesConfig(
            last_context=context,
            last_namespace=namespace,
        )

    def _save_config(self) -> None:
        """
        Save the configuration to the kubernetes configuration file.
        """
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w") as config_file:
            yaml.dump(self.kubernetes_config.to_dict(), config_file)

    def _reload_cache_lazy(self) -> None:
        """
        Reload the configuration cache if the file has been modified.
        """
        if self.config_path.exists():
            mtime = os.path.getmtime(self.config_path)
            if self._cached_mtime != mtime:
                self._load_config()
                self._cached_mtime = mtime
        else:
            self.kubernetes_config = KubernetesConfig()
            self._cached_mtime = None

    def _set_last_context(self, context: str) -> None:
        """
        Set the Kubernetes context.

        Parameters
        ----------
        context : str
            The Kubernetes context to set.
        """
        if self.kubernetes_config.last_context != context:
            self.kubernetes_config.last_context = context
            self._save_config()
            self._reload_cache_lazy()

    def _set_last_namespace(self, namespace: str) -> None:
        """
        Set the Kubernetes namespace.

        Parameters
        ----------
        namespace : str
            The Kubernetes namespace to set.
        """
        if self.kubernetes_config.last_namespace != namespace:
            self.kubernetes_config.last_namespace = namespace
            self._save_config()
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
        _all_contexts, active_context = k8s_config.list_kube_config_contexts()
        if not context:
            context = active_context["name"]

        if not namespace:
            namespace = active_context["context"].get("namespace", "default")

        return context, namespace

    def _compare_config_variable(
        self,
        variable: K8SConfigVariable,
        current_value: str,
        last_value: str,
        set_func: Callable,
    ) -> None:
        """
        Compare a configuration variable with the last used value.

        Parameters
        ----------
        variable : K8SConfigVariables
            The variable to compare.
        current_value : str
            The current value of the variable.
        last_value : str
            The last used value of the variable.
        """
        if not last_value:
            set_func(current_value)
        elif last_value != current_value:
            warning(f"Are you using the correct {variable.value}?")
            warning(
                f"Current {variable.value}: {Fore.YELLOW}{current_value}"
                f"{Style.RESET_ALL}"
            )
            warning(
                f"Last    {variable.value}: {Fore.YELLOW}{last_value}{Style.RESET_ALL}"
            )

            new_value = questionary.select(
                f"Which {variable.value} do you want to use?",
                choices=[current_value, last_value],
                default=current_value,
            ).unsafe_ask()
            set_func(new_value)

    def select_k8s_config(
        self,
        context: str | None = None,
        namespace: str | None = None,
    ) -> KubernetesConfig:
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
        self._load_config()

        # compare context
        self._compare_config_variable(
            variable=K8SConfigVariable.CONTEXT,
            current_value=active_context,
            last_value=self.kubernetes_config.last_context,
            set_func=self._set_last_context,
        )

        # compare namespace
        self._compare_config_variable(
            variable=K8SConfigVariable.NAMESPACE,
            current_value=active_namespace,
            last_value=self.kubernetes_config.last_namespace,
            set_func=self._set_last_namespace,
        )

        # only print the context and namespace once. This is to avoid printing it many
        # times, e.g. in sandbox commands
        global _CONTEXT_INFO_PRINTED
        if not _CONTEXT_INFO_PRINTED:
            info(
                f"Using    context: {Fore.YELLOW}{self.kubernetes_config.last_context}"
                f"{Style.RESET_ALL}"
            )
            info(
                f"Using  namespace: {Fore.YELLOW}"
                f"{self.kubernetes_config.last_namespace}{Style.RESET_ALL}"
            )
            _CONTEXT_INFO_PRINTED = True

        return self.kubernetes_config


def select_k8s_config(
    context: str | None = None,
    namespace: str | None = None,
) -> KubernetesConfig:
    """
    Select the Kubernetes context and namespace.

    Parameters
    ----------
    context : str or None, optional
        The Kubernetes context to use.
    namespace : str or None, optional
        The Kubernetes namespace to use.

    Returns
    -------
    KubernetesConfig
        Object with the selected Kubernetes configuration.
    """
    k8s_config_manager = K8SConfigManager()
    return k8s_config_manager.select_k8s_config(context=context, namespace=namespace)
