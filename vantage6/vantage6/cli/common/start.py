from __future__ import annotations

import subprocess
from os import PathLike
from pathlib import Path

from vantage6.common import error, info
from vantage6.common.context import AppContext
from vantage6.common.globals import (
    DEFAULT_CHART_REPO,
    InstanceType,
)

from vantage6.cli.common.utils import check_running
from vantage6.cli.globals import ChartName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils import check_config_name_allowed, validate_input_cmd_args


def prestart_checks(
    ctx: AppContext,
    instance_type: InstanceType,
    name: str,
    system_folders: bool,
) -> None:
    """
    Run pre-start checks for an instance.
    """
    check_config_name_allowed(name)

    if check_running(ctx.helm_release_name, instance_type, name, system_folders):
        error(f"Instance '{name}' is already running.")
        exit(1)


def helm_install(
    release_name: str,
    chart_name: ChartName,
    values_file: str | PathLike | None = None,
    k8s_config: KubernetesConfig | None = None,
    local_chart_dir: str | None = None,
    custom_values: list[str] | None = None,
    chart_version: str | None = None,
) -> None:
    """
    Manage the `helm install` command.

    Parameters
    ----------
    release_name : str
        The name of the Helm release.
    chart_name : str
        The name of the Helm chart.
    values_file : str, optional
        A single values file to use with the `-f` flag.
    k8s_config : KubernetesConfig, optional
        The Kubernetes configuration to use.
    local_chart_dir : str, optional
        The local directory containing the Helm charts.
    custom_values : list[str], optional
        Custom values to pass to the Helm chart, that override the values in the values
        file. Each item in the list is a string in the format "key=value".
    chart_version : str, optional
        The version of the Helm chart to use.
    """
    # Input validation
    validate_input_cmd_args(release_name, "release name")
    validate_input_cmd_args(chart_name, "chart name")

    values_file = Path(values_file) if values_file else None
    if values_file and not values_file.is_file():
        error(f"Helm chart values file does not exist: {values_file}")
        return

    if k8s_config:
        validate_input_cmd_args(
            k8s_config.context, "k8s_config.context", allow_none=True
        )
        validate_input_cmd_args(
            k8s_config.namespace, "k8s_config.namespace", allow_none=True
        )

    if local_chart_dir and local_chart_dir.rstrip("/").endswith(chart_name.value):
        local_chart_dir = str(Path(local_chart_dir).parent)

    # Create the command
    if local_chart_dir:
        command = [
            "helm",
            "install",
            release_name,
            f"{local_chart_dir}/{chart_name.value}",
        ]
    else:
        command = [
            "helm",
            "install",
            release_name,
            chart_name,
            "--repo",
            DEFAULT_CHART_REPO,
            # TODO v5+ remove this flag when we have a stable release
            "--devel",
        ]
        if chart_version:
            command.extend(["--version", chart_version])

    if values_file:
        command.extend(["-f", str(values_file)])

    if k8s_config.context:
        command.extend(["--kube-context", k8s_config.context])

    if k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])

    if custom_values:
        for custom_value in custom_values:
            command.extend(["--set", custom_value])

    try:
        subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            check=True,
        )
        info(
            f"Successfully installed release '{release_name}' using chart "
            f"'{chart_name.value}'."
        )
    except subprocess.CalledProcessError:
        error(f"Failed to install release '{release_name}'.")
        exit(1)
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
        exit(1)
