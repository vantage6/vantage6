import os
from os import PathLike
from colorama import Fore, Style
from pathlib import Path
import yaml
from vantage6.common import error, warning, info
from vantage6.cli.globals import (
    DEFAULT_CLI_CONFIG_FILE,
    DEFAULT_HELM_CHART_FOLDER,
    ChartType,
)
from kubernetes import config
import questionary


"""
The config.yaml has following structure:

---
kube:
  last_context: <last_used_k8s_context>
  last_namespace: <last_used_k8s_namespace>
auth:
  default_chart: <last_used_auth>
  last_chart: <last_used_auth>
node:
  default_chart: <last_used_node>
  last_chart: <last_used_node>
server:
  default_chart: <last_used_server>
  last_chart: <last_used_server>
store:
  default_chart: <last_used_store>
  last_chart: <last_used_store>
---

`kube` is the Kubernetes context and namespace used last time by the CLI operations.
`default_chart` is used by default if no chart is provided by user. If no chart
  is set, it defaults corresponding chart in the `DEFAULT_HELM_CHART_FOLDER`.
`last_chart` is the chart used last time by the CLI operations.
"""


class CliConfig:
    """
    A class to manage CLI configuration for Kubernetes contexts and Helm charts.

    Attributes:
        config_path (PathLike): Path to the configuration file.
        _cached_config (dict | None): Cached configuration data.
        _cached_mtime (float | None): Last modification time of the configuration file.
    """

    def __init__(self, config_path: str | PathLike = DEFAULT_CLI_CONFIG_FILE) -> None:
        """
        Initialize the CliConfig object.

        Args:
            config_path: Path to the configuration file.
        """
        self.config_path: PathLike = Path(config_path)
        self._cached_config: dict | None = None
        self._cached_mtime: float | None = None

    def _load_config(self) -> dict:
        """
        Load the configuration from the file.

        Returns:
            dict: The loaded configuration data.
        """
        if self.config_path.exists():
            with open(self.config_path, "r") as config_file:
                return yaml.safe_load(config_file) or {}
        # warning(
        #     f"Configuration file {Fore.YELLOW}{self.config_path}{Style.RESET_ALL} does not exist."
        # )
        return {}

    def _save_config(self, config: dict) -> None:
        """
        Save the configuration to the file.

        Args:
            config: The configuration data to save.
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
            # warning(
            #     f"Configuration file {Fore.YELLOW}{self.config_path}{Style.RESET_ALL} does not exist."
            # )
            self._cached_config = {}
            self._cached_mtime = None

    def get_last_context(self) -> str | None:
        """
        Get the last used Kubernetes context.

        Returns:
            str | None: The last used Kubernetes context, or None if not set.
        """
        self._reload_cache_lazy()
        return self._cached_config.get("kube", {}).get("last_context")

    def set_last_context(self, context: str) -> None:
        """
        Set the Kubernetes context.

        Args:
            context: The Kubernetes context to set.
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

        Returns:
            str | None: The last used Kubernetes namespace, or None if not set.
        """
        self._reload_cache_lazy()
        return self._cached_config.get("kube", {}).get("last_namespace")

    def set_last_namespace(self, namespace: str) -> None:
        """
        Set the Kubernetes namespace.

        Args:
            namespace: The Kubernetes namespace to set.
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

    def get_default_chart(self, chart_type: ChartType) -> str:
        """
        Get the default Helm chart path for a specific chart type.

        If default chart is empty in config file, it returns the chart in
        `DEFAULT_HELM_CHART_FOLDER`.

        Args:
            chart_type: The type of chart.

        Returns:
            str: The default Helm chart path for the specified chart type.
        """
        self._reload_cache_lazy()
        return self._cached_config.get(chart_type, {}).get(
            "default_chart", str(DEFAULT_HELM_CHART_FOLDER / chart_type)
        )

    def set_default_chart(self, chart: str, chart_type: ChartType) -> None:
        """
        Set the default Helm chart path for a specific chart type.

        Args:
            chart: The Helm chart path to set as default.
            chart_type: The type of chart.
        """
        config = self._load_config()
        if chart_type not in config:
            config[chart_type] = {}

        if config[chart_type].get("default_chart") != chart:
            validate_helm_chart(chart)
            config[chart_type]["default_chart"] = chart
            # remove last chart if it exists
            if "last_chart" in config[chart_type]:
                del config[chart_type]["last_chart"]
            self._save_config(config)
            self._reload_cache_lazy()
        info(
            f"Successfully set default Helm chart for {chart_type} to"
            f" {Fore.YELLOW}{chart}{Style.RESET_ALL}"
        )

    def get_last_chart(self, chart_type: ChartType) -> str | None:
        """
        Get the last used Helm chart path for a specific chart type.

        Args:
            chart_type: The type of chart.

        Returns:
            str | None: The last used Helm chart path for the specified chart
                type, or None if not set.
        """
        self._reload_cache_lazy()
        return self._cached_config.get(chart_type, {}).get("last_chart")

    def set_last_chart(self, chart: str, chart_type: ChartType) -> None:
        """
        Set the last used Helm chart path for a specific chart type.

        Args:
            chart: The Helm chart path to set as last used.
            chart_type: The type of chart.
        """
        config = self._load_config()
        if chart_type not in config:
            config[chart_type] = {}

        if config[chart_type].get("last_chart") != chart:
            validate_helm_chart(chart)
            config[chart_type]["last_chart"] = chart
            self._save_config(config)
            self._reload_cache_lazy()

    def get_active_settings(
        self,
        chart_type: ChartType,
        context: str | None,
        namespace: str | None,
        chart: str | None,
    ) -> tuple[str, str, str]:
        """
        Get the active Kubernetes context, namespace, and Helm chart.

        Args:
            chart_type: The type of chart.
            context: The Kubernetes context to use.
            namespace: The Kubernetes namespace to use.
            chart: The Helm chart to use.

        Returns:
            tuple[str, str, str]: A tuple containing the active context, namespace, and chart path.
        """
        if not context:
            _, active_context = config.list_kube_config_contexts()
            context = active_context["name"]

        if not namespace:
            namespace = active_context["context"].get("namespace", "default")

        if not chart:
            chart = self.get_default_chart(chart_type)

        return context, namespace, chart

    def compare_changes_config(
        self,
        chart_type: ChartType,
        context: str | None = None,
        namespace: str | None = None,
        chart: str | None = None,
    ) -> None:
        """
        Compare active settings with last used settings.

        Args:
            chart_type: The type of chart.
            context: The Kubernetes context to use.
            namespace: The Kubernetes namespace to use.
            chart: The Helm chart to use.
        """

        active_context, active_namespace, active_chart = self.get_active_settings(
            chart_type, context, namespace, chart
        )
        last_context = self.get_last_context()
        last_namespace = self.get_last_namespace()
        last_chart = self.get_last_chart(chart_type)

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

        # compare chart
        if not last_chart:
            self.set_last_chart(active_chart, chart_type)
        elif last_chart != active_chart:
            warning("Are you using the correct Helm chart?")
            warning(f"Current chart: {Fore.YELLOW}{active_chart}{Style.RESET_ALL}")
            warning(f"Last    chart: {Fore.YELLOW}{last_chart}{Style.RESET_ALL}")

            active_chart = questionary.select(
                "Which Helm chart do you want to use?",
                choices=[active_chart, last_chart],
                default=active_chart,
            ).ask()

            if last_chart != active_chart:
                self.set_last_chart(active_chart, chart_type)

        info(f"Using    context: {Fore.YELLOW}{active_context}{Style.RESET_ALL}")
        info(f"Using  namespace: {Fore.YELLOW}{active_namespace}{Style.RESET_ALL}")
        info(f"Using Helm chart: {Fore.YELLOW}{active_chart}{Style.RESET_ALL}")
        return active_context, active_namespace, active_chart


# TODO: add proper validation for helm chart
def validate_helm_chart(chart: str) -> bool:
    """
    Validate that the given path is a valid Helm chart.

    Args:
        chart: The path to the Helm chart.

    Returns:
        bool: True if the path is a valid Helm chart, False otherwise.
    """
    path = Path(chart)
    if not (path / "Chart.yaml").exists():
        error(f"Chart.yaml NOT exist in: {Fore.YELLOW}{chart}{Style.RESET_ALL}")
        exit(1)

    if not (path / "values.yaml").exists():
        warning(f"values.yaml NOT exist in: {Fore.YELLOW}{chart}{Style.RESET_ALL}")
        exit(1)
