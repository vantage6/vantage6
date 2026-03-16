from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

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

    return EnvoyGatewayStatus(exists=False)


def _wait_for_envoy_gateway_ready(
    k8s_config: KubernetesConfig,
    namespace: str = _DEFAULT_ENVOY_GATEWAY_NAMESPACE,
    timeout_seconds: int = 600,
) -> None:
    """
    Wait for the Envoy Gateway deployment and its load balancer Service to be ready.
    """

    info("Waiting for Envoy Gateway to become ready...")
    end_time = time.time() + timeout_seconds

    # Wait for the envoy-gateway deployment to be Available.
    while time.time() < end_time:
        cmd = [
            "kubectl",
            "get",
            "deployment",
            "-l",
            "app.kubernetes.io/name=envoy-gateway",
            "-n",
            namespace,
            "-o",
            'jsonpath={.items[0].status.conditions[?(@.type=="Available")].status}',
        ]
        if k8s_config.context:
            cmd.extend(["--context", k8s_config.context])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.stdout.strip() == "True":
            break
        time.sleep(5)

    # Give the Service time to obtain an external IP/hostname (best effort).
    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        cmd = [
            "kubectl",
            "get",
            "svc",
            "-l",
            "app.kubernetes.io/name=envoy-gateway",
            "-n",
            namespace,
            "-o",
            "jsonpath={.items[0].status.loadBalancer.ingress[0].ip}|"
            "{.items[0].status.loadBalancer.ingress[0].hostname}",
        ]
        if k8s_config.context:
            cmd.extend(["--context", k8s_config.context])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        if (
            result.returncode == 0
            and result.stdout.strip()
            and result.stdout.strip() != "|"
        ):
            break
        time.sleep(5)


def ensure_envoy_gateway(
    k8s_config: KubernetesConfig,
    auto_install: bool = True,
) -> EnvoyGatewayStatus:
    """
    Ensure that an Envoy Gateway installation is available in the cluster.

    If an appropriate GatewayClass already exists, it is reused. Otherwise, if
    `auto_install` is True, this function attempts to install Envoy Gateway via
    its official Helm chart (including Gateway API CRDs).
    """

    status = _detect_envoy_gateway(k8s_config)
    if status.exists:
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
        raise SystemExit(1)

    info(
        "No suitable Envoy Gateway installation detected. Installing Envoy Gateway "
        "via Helm..."
    )

    # Install Envoy Gateway via Helm using the OCI chart that also installs the
    # required Gateway API CRDs.
    try:
        subprocess.run(
            [
                "helm",
                "upgrade",
                "--install",
                _DEFAULT_ENVOY_GATEWAY_RELEASE,
                "oci://docker.io/envoyproxy/gateway-helm",
                "--version",
                "v1.6.5",
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
        raise SystemExit(exc.returncode)

    _wait_for_envoy_gateway_ready(
        k8s_config, namespace=_DEFAULT_ENVOY_GATEWAY_NAMESPACE
    )

    # Re-run detection to populate status.
    return _detect_envoy_gateway(k8s_config)
