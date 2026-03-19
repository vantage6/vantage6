from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

import requests

from vantage6.common import error, info

from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig

_DEFAULT_ENVOY_GATEWAY_NAMESPACE = "envoy-gateway-system"
_DEFAULT_ENVOY_GATEWAY_RELEASE = "eg"
_DEFAULT_ENVOY_GATEWAY_CLASS_NAME = "envoy-gateway"
_ENVOY_GATEWAY_CONTROLLER = "gateway.envoyproxy.io/gatewayclass-controller"


@dataclass
class EnvoyGatewayStatus:
    """
    Simple status object describing an Envoy Gateway installation.
    """

    exists: bool
    gateway_class: str | None = None
    namespace: str | None = None


def _get_latest_envoy_gateway_version() -> str:
    """
    Get the latest Envoy Gateway release tag from GitHub.

    Raises a RuntimeError if lookup fails so the caller can decide whether to
    require an explicit version.
    """
    github_api_url = "https://api.github.com/repos/envoyproxy/gateway/releases/latest"

    headers = {"Accept": "application/vnd.github.v3+json"}
    try:
        response = requests.get(github_api_url, timeout=5, headers=headers)
        response.raise_for_status()
        release_data = response.json()
        version = release_data.get("tag_name")
        if not version:
            raise RuntimeError(
                "No tag_name found in Envoy Gateway GitHub releases response."
            )
        return version
    except Exception as exc:
        raise RuntimeError(
            f"Failed to fetch latest Envoy Gateway version from GitHub: {exc!r}"
        ) from exc


def _ensure_envoy_gateway_class(k8s_config: KubernetesConfig) -> None:
    """
    Ensure an Envoy GatewayClass exists so Gateway resources can be accepted.
    """
    manifest = f"""apiVersion: gateway.networking.k8s.io/v1
kind: GatewayClass
metadata:
  name: {_DEFAULT_ENVOY_GATEWAY_CLASS_NAME}
spec:
  controllerName: {_ENVOY_GATEWAY_CONTROLLER}
"""
    result = run_kubectl_command(
        ["apply", "-f", "-"],
        k8s_config,
        check=False,
        use_k8s_config_namespace=False,
        input_text=manifest,
    )
    if result.returncode != 0:
        error(
            "❌ Failed to create or update GatewayClass for Envoy Gateway. "
            "Please create a GatewayClass manually."
        )
        exit(1)


def _detect_envoy_gateway(
    k8s_config: KubernetesConfig,
    gateway_class_name: str = _DEFAULT_ENVOY_GATEWAY_CLASS_NAME,
) -> EnvoyGatewayStatus:
    """
    Try to detect an Envoy Gateway installation by looking for a GatewayClass
    managed by the Envoy Gateway controller.
    """
    try:
        result = run_kubectl_command(
            [
                "get",
                "gatewayclass",
                "-o",
                "jsonpath={range .items[*]}{.metadata.name}:{.spec.controller}{'\\n'}{end}",
            ],
            k8s_config,
            check=False,
            use_k8s_config_namespace=False,
        )
        if result.returncode == 0 and result.stdout:
            for line in result.stdout.strip().splitlines():
                try:
                    name, controller = line.split(":", 1)
                except ValueError:
                    continue
                controller = controller.strip()
                if (
                    controller == _ENVOY_GATEWAY_CONTROLLER
                    or name == gateway_class_name
                ):
                    return EnvoyGatewayStatus(
                        exists=True,
                        gateway_class=name,
                        namespace=_DEFAULT_ENVOY_GATEWAY_NAMESPACE,
                    )
    except Exception:
        # Best-effort detection; fall through to "not found".
        pass

    # Fallback: detect the installed Envoy Gateway controller deployment even if
    # no GatewayClass has been created yet.
    try:
        result = run_kubectl_command(
            [
                "get",
                "deployment",
                "-n",
                _DEFAULT_ENVOY_GATEWAY_NAMESPACE,
                "-l",
                "control-plane=envoy-gateway",
                "-o",
                "jsonpath={.items[0].metadata.name}:{.items[0].status.conditions[?(@.type=='Available')].status}",
            ],
            k8s_config,
            check=False,
            use_k8s_config_namespace=False,
        )
        if result.returncode == 0 and result.stdout:
            name, _, available = result.stdout.partition(":")
            if name and available.strip() == "True":
                return EnvoyGatewayStatus(
                    exists=True,
                    gateway_class=gateway_class_name,
                    namespace=_DEFAULT_ENVOY_GATEWAY_NAMESPACE,
                )
    except Exception:
        pass

    return EnvoyGatewayStatus(exists=False)


def _wait_for_envoy_gateway_ready(
    k8s_config: KubernetesConfig,
    namespace: str = _DEFAULT_ENVOY_GATEWAY_NAMESPACE,
    timeout_seconds: int = 600,
) -> None:
    """
    Wait for the Envoy Gateway controller deployment to be available.

    Exits if the controller does not become available within the given timeout.
    """

    info("Waiting for Envoy Gateway to become ready...")
    end_time = time.time() + timeout_seconds

    # Wait for the envoy-gateway deployment to be Available.
    while time.time() < end_time:
        result = run_kubectl_command(
            [
                "get",
                "deployment",
                "-l",
                "control-plane=envoy-gateway",
                "-n",
                namespace,
                "-o",
                'jsonpath={.items[0].status.conditions[?(@.type=="Available")].status}',
            ],
            k8s_config,
            check=False,
            use_k8s_config_namespace=False,
        )
        if result.stdout.strip() == "True":
            info("Envoy Gateway controller is available.")
            return

        time.sleep(5)

    error(
        "❌ Timed out waiting for Envoy Gateway controller to become available. "
        "Please check the Envoy Gateway installation (pods, events, and logs) "
        "and try again."
    )
    exit(1)


def ensure_envoy_gateway(
    k8s_config: KubernetesConfig,
    auto_install: bool = True,
    version: str | None = None,
) -> EnvoyGatewayStatus:
    """
    Ensure that an Envoy Gateway installation is available in the cluster.

    If an appropriate GatewayClass already exists, it is reused. Otherwise, if
    `auto_install` is True, this function attempts to install Envoy Gateway via
    its official Helm chart (including Gateway API CRDs).
    """

    status = _detect_envoy_gateway(k8s_config)
    if status.exists:
        _ensure_envoy_gateway_class(k8s_config)
        info(
            "✅ Found existing Envoy Gateway installation "
            f"(GatewayClass='{status.gateway_class or _DEFAULT_ENVOY_GATEWAY_CLASS_NAME}')."
        )
        return status

    if not auto_install:
        error(
            "⚠️  No Envoy Gateway installation detected and automatic installation "
            "is disabled. If hub gateway is enabled, you must install Envoy Gateway "
            "manually or disable hubGateway.enabled."
        )
        exit(1)

    info(
        "No suitable Envoy Gateway installation detected. Installing Envoy Gateway "
        "via Helm..."
    )

    # Install Envoy Gateway via Helm using the OCI chart that also installs the
    # required Gateway API CRDs.
    if version is None:
        try:
            version = _get_latest_envoy_gateway_version()
        except RuntimeError as exc:
            error(str(exc))
            error(
                "Please re-run 'v6 hub start' with --envoy-gateway-version to specify "
                "the Envoy Gateway version explicitly."
            )
            exit(1)

    try:
        subprocess.run(
            [
                "helm",
                "upgrade",
                "--install",
                _DEFAULT_ENVOY_GATEWAY_RELEASE,
                "oci://docker.io/envoyproxy/gateway-helm",
                "--version",
                version,
                "--namespace",
                _DEFAULT_ENVOY_GATEWAY_NAMESPACE,
                "--create-namespace",
            ],
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        error(
            "❌ Failed to install Envoy Gateway via Helm. "
            "Please install Envoy Gateway manually following the official "
            "documentation."
        )
        exit(exc.returncode)

    _wait_for_envoy_gateway_ready(
        k8s_config, namespace=_DEFAULT_ENVOY_GATEWAY_NAMESPACE
    )
    _ensure_envoy_gateway_class(k8s_config)

    # Re-run detection to populate status.
    return _detect_envoy_gateway(k8s_config)
