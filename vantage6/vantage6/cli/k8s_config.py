import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import appdirs
import questionary
import yaml
from colorama import Fore, Style
from kubernetes import config as k8s_config

from vantage6.common import error, info, warning
from vantage6.common.enum import StrEnumBase
from vantage6.common.globals import APPNAME

from vantage6.cli.globals import DEFAULT_CLI_CONFIG_FILE
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling

_CONTEXT_INFO_PRINTED = False


class K8SConfigVariable(StrEnumBase):
    """
    Enum containing the variables of the Kubernetes configuration.
    """

    CONTEXT = "context"
    NAMESPACE = "namespace"
    K8S_NODE = "k8s node"


@dataclass
class KubernetesConfig:
    """
    Class to store Kubernetes configuration.

    Attributes
    ----------
    context : str or None
        The last used Kubernetes context.
    namespace : str or None
        The last used Kubernetes namespace.
    k8s_node : str or None
        The last used Kubernetes node.
    """

    context: str | None = None
    namespace: str | None = None
    k8s_node: str | None = None

    def to_dict(self) -> dict:
        """
        Convert the Kubernetes configuration to a dictionary.
        """
        output = {}
        if self.context:
            output["context"] = self.context
        if self.namespace:
            output["namespace"] = self.namespace
        if self.k8s_node:
            output["k8s_node"] = self.k8s_node
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

        context = loaded_config.get("context")
        namespace = loaded_config.get("namespace")
        k8s_node = loaded_config.get("k8s_node")
        self.kubernetes_config = KubernetesConfig(
            context=context,
            namespace=namespace,
            k8s_node=k8s_node,
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

    def _set_context(self, context: str) -> None:
        """
        Set the Kubernetes context.

        Parameters
        ----------
        context : str
            The Kubernetes context to set.
        """
        if self.kubernetes_config.context != context:
            self.kubernetes_config.context = context
            self._save_config()
            self._reload_cache_lazy()

    def _set_namespace(self, namespace: str) -> None:
        """
        Set the Kubernetes namespace.

        Parameters
        ----------
        namespace : str
            The Kubernetes namespace to set.
        """
        if self.kubernetes_config.namespace != namespace:
            self.kubernetes_config.namespace = namespace
            self._save_config()
            self._reload_cache_lazy()

    def _set_k8s_node(self, k8s_node: str) -> None:
        """
        Set the Kubernetes node.
        """
        if self.kubernetes_config.k8s_node != k8s_node:
            self.kubernetes_config.k8s_node = k8s_node
            self._save_config()
            self._reload_cache_lazy()

    def get_active_settings(
        self, input_k8s_config: KubernetesConfig
    ) -> KubernetesConfig:
        """
        Get the active Kubernetes configuration.

        Parameters
        ----------
        input_k8s_config : KubernetesConfig
            The Kubernetes configuration to use.

        Returns
        -------
        KubernetesConfig
            An object containing the active context, namespace and k8s node.
        """
        # start by creating copy of the input_k8s_config
        active_k8s_config = KubernetesConfig(
            context=input_k8s_config.context,
            namespace=input_k8s_config.namespace,
            k8s_node=input_k8s_config.k8s_node,
        )

        _all_contexts, active_context = k8s_config.list_kube_config_contexts()
        if not active_k8s_config.context:
            active_k8s_config.context = active_context["name"]

        if not active_k8s_config.namespace:
            active_k8s_config.namespace = active_context["context"].get(
                "namespace", "default"
            )

        if not active_k8s_config.k8s_node:
            # Get node names from Kubernetes API
            try:
                core_api = get_core_api_with_ssl_handling()
                nodes = core_api.list_node()
                if nodes.items:
                    active_k8s_config.k8s_node = nodes.items[0].metadata.name
                else:
                    active_k8s_config.k8s_node = None
            except Exception:
                error("Failed to get Kubernetes nodes")
                active_k8s_config.k8s_node = None

        return active_k8s_config

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
        input_k8s_config: KubernetesConfig,
    ) -> KubernetesConfig:
        """
        Compare active settings with last used settings.

        Parameters
        ----------
        input_k8s_config : KubernetesConfig
            The Kubernetes configuration to use.

        Returns
        -------
        KubernetesConfig
            An object containing the active context, namespace and k8s node.
        """

        active_k8s_config = self.get_active_settings(input_k8s_config)
        self._load_config()

        # compare context
        self._compare_config_variable(
            variable=K8SConfigVariable.CONTEXT,
            current_value=active_k8s_config.context,
            last_value=self.kubernetes_config.context,
            set_func=self._set_context,
        )

        # compare namespace
        self._compare_config_variable(
            variable=K8SConfigVariable.NAMESPACE,
            current_value=active_k8s_config.namespace,
            last_value=self.kubernetes_config.namespace,
            set_func=self._set_namespace,
        )

        # compare k8s node
        self._compare_config_variable(
            variable=K8SConfigVariable.K8S_NODE,
            current_value=active_k8s_config.k8s_node,
            last_value=self.kubernetes_config.k8s_node,
            set_func=self._set_k8s_node,
        )

        # only print the context and namespace once. This is to avoid printing it many
        # times, e.g. in sandbox commands
        global _CONTEXT_INFO_PRINTED
        if not _CONTEXT_INFO_PRINTED:
            info(
                f"Using    context: {Fore.YELLOW}{self.kubernetes_config.context}"
                f"{Style.RESET_ALL}"
            )
            info(
                f"Using  namespace: {Fore.YELLOW}"
                f"{self.kubernetes_config.namespace}{Style.RESET_ALL}"
            )
            info(
                f"Using   k8s node: {Fore.YELLOW}"
                f"{self.kubernetes_config.k8s_node}{Style.RESET_ALL}"
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
    return k8s_config_manager.select_k8s_config(
        KubernetesConfig(context=context, namespace=namespace)
    )
