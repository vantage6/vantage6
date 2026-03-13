from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass

from vantage6.common import error, info, warning

from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig

_DEFAULT_INGRESS_NAMESPACE = "ingress-nginx"
_DEFAULT_INGRESS_RELEASE = "ingress-nginx"
_DEFAULT_INGRESS_CLASS_NAME = "nginx"
_DEFAULT_INGRESS_CONTROLLER_VALUE = "k8s.io/ingress-nginx"


@dataclass
class IngressControllerStatus:
    """
    Simple status object describing an ingress controller instance.
    """

    exists: bool
    ingress_class: str | None = None
    service_name: str | None = None
    namespace: str | None = None
    external_ip_or_hostname: str | None = None


def _detect_ingress_controller(
    k8s_config: KubernetesConfig,
    ingress_class_name: str = _DEFAULT_INGRESS_CLASS_NAME,
) -> IngressControllerStatus:
    """
    Try to detect an ingress-nginx controller and its external endpoint.

    The detection is intentionally conservative: it first looks for an
    IngressClass with the given name or matching the standard nginx controller
    value, and then for a LoadBalancer Service that exposes it.
    """

    # 1) Check for an IngressClass with the expected name or controller value.
    try:
        result = run_kubectl_command(
            [
                "get",
                "ingressclass",
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
                    name == ingress_class_name
                    or controller == _DEFAULT_INGRESS_CONTROLLER_VALUE
                ):
                    ingress_class = name
                    break
            else:
                ingress_class = None
        else:
            ingress_class = None
    except Exception:
        ingress_class = None

    # 2) Look for a LoadBalancer Service that belongs to ingress-nginx.
    try:
        svc_result = run_kubectl_command(
            [
                "get",
                "svc",
                "-A",
                "-l",
                "app.kubernetes.io/name=ingress-nginx,app.kubernetes.io/component=controller",
                "-o",
                "jsonpath={range .items[*]}{.metadata.namespace}:{.metadata.name}:"
                "{.spec.type}:{.status.loadBalancer.ingress[0].ip}"
                "{'|'}{.status.loadBalancer.ingress[0].hostname}{'\\n'}{end}",
            ],
            k8s_config,
            check=False,
        )
    except Exception:
        svc_result = None

    svc_ns = svc_name = lb_ip = lb_hostname = None
    if svc_result and svc_result.returncode == 0 and svc_result.stdout:
        for line in svc_result.stdout.strip().splitlines():
            # namespace:name:type:ip|hostname
            parts = line.split(":")
            if len(parts) < 4:
                continue
            ns, name, svc_type, tail = parts[0], parts[1], parts[2], ":".join(parts[3:])
            if svc_type != "LoadBalancer":
                continue
            ip, _, hostname = tail.partition("|")
            lb_ip = ip or None
            lb_hostname = hostname or None
            svc_ns = ns
            svc_name = name
            break

    if ingress_class or svc_name:
        return IngressControllerStatus(
            exists=True,
            ingress_class=ingress_class or ingress_class_name,
            service_name=svc_name,
            namespace=svc_ns,
            external_ip_or_hostname=lb_ip or lb_hostname,
        )

    return IngressControllerStatus(exists=False)


def _wait_for_ingress_controller_ready(
    k8s_config: KubernetesConfig,
    namespace: str = _DEFAULT_INGRESS_NAMESPACE,
    timeout_seconds: int = 600,
) -> None:
    """
    Wait for the ingress-nginx controller Deployment and Service to be ready.
    """

    info("Waiting for NGINX ingress controller to become ready...")
    end_time = time.time() + timeout_seconds

    # Wait for the controller deployment to be Available.
    while time.time() < end_time:
        cmd = [
            "kubectl",
            "get",
            "deployment",
            f"{_DEFAULT_INGRESS_RELEASE}-controller",
            "-n",
            namespace,
            "-o",
            'jsonpath={.status.conditions[?(@.type=="Available")].status}',
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

    # Wait for the Service to have an external IP or hostname.
    while time.time() < end_time:
        cmd = [
            "kubectl",
            "get",
            "svc",
            f"{_DEFAULT_INGRESS_RELEASE}-controller",
            "-n",
            namespace,
            "-o",
            "jsonpath={.status.loadBalancer.ingress[0].ip}|"
            "{.status.loadBalancer.ingress[0].hostname}",
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


def ensure_ingress_controller(
    k8s_config: KubernetesConfig,
    ingress_class_name: str = _DEFAULT_INGRESS_CLASS_NAME,
    auto_install: bool = True,
    azure: bool = True,
) -> IngressControllerStatus:
    """
    Ensure that a suitable NGINX ingress controller is available.

    If an appropriate controller already exists, it is reused. Otherwise, if
    `auto_install` is True, this function attempts to install the official
    `ingress-nginx` Helm chart into the cluster.

    Returns a status object describing the resulting controller.
    """

    status = _detect_ingress_controller(k8s_config, ingress_class_name)
    if status.exists:
        endpoint = status.external_ip_or_hostname or "<no-external-endpoint-yet>"
        info(
            f"✅ Found existing ingress controller (class='{status.ingress_class}', "
            f"service='{status.namespace}/{status.service_name}', endpoint='{endpoint}')."
        )
        return status

    if not auto_install:
        error(
            "⚠️  No ingress controller detected and automatic installation is disabled. "
            "If hub ingress is enabled, you must install an ingress controller "
            "manually (for example ingress-nginx) or disable hubIngress.enabled."
        )
        exit(1)

    info(
        "No suitable ingress controller detected. Installing ingress-nginx using Helm..."
    )

    # Install ingress-nginx via Helm. We intentionally run Helm directly here
    # instead of through the hub chart to keep responsibilities separated.
    try:
        # Add the Helm repo (idempotent; ignore failure if it already exists).
        subprocess.run(
            [
                "helm",
                "repo",
                "add",
                "ingress-nginx",
                "https://kubernetes.github.io/ingress-nginx",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        subprocess.run(
            ["helm", "repo", "update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

        cmd = [
            "helm",
            "upgrade",
            "--install",
            _DEFAULT_INGRESS_RELEASE,
            "ingress-nginx/ingress-nginx",
            "--namespace",
            _DEFAULT_INGRESS_NAMESPACE,
            "--create-namespace",
            "--set",
            f"controller.ingressClassResource.name={ingress_class_name}",
            "--set",
            f"controller.ingressClassResource.controllerValue={_DEFAULT_INGRESS_CONTROLLER_VALUE}",
            "--set",
            "controller.ingressClassByName=true",
            "--set",
            "controller.service.type=LoadBalancer",
        ]
        if azure:
            # These settings are necessary with Azure Kubernetes, as otherwise external
            # IP is not reachable (see also
            # https://stackoverflow.com/a/79144660/5398197).
            cmd.extend(
                [
                    "--set",
                    'controller.service.annotations."service\\.beta\\.kubernetes\\.io/azure-load-balancer-health-probe-request-path"=/healthz',
                    "--set",
                    "controller.service.externalTrafficPolicy=Local",
                ]
            )
        if k8s_config.context:
            cmd.extend(["--kube-context", k8s_config.context])

        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            check=True,
        )
    except subprocess.CalledProcessError:
        error("❌ Failed to install ingress-nginx via Helm.")
        error(
            "Please install an ingress controller manually or re-run with "
            "--no-auto-install-ingress."
        )
        exit(1)
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available "
            "in the PATH."
        )
        exit(1)

    # Wait for the controller to be ready and obtain an external endpoint.
    _wait_for_ingress_controller_ready(k8s_config, namespace=_DEFAULT_INGRESS_NAMESPACE)

    status = _detect_ingress_controller(k8s_config, ingress_class_name)
    endpoint = status.external_ip_or_hostname or "<no-external-endpoint-yet>"
    if status.exists:
        info(
            "✅ NGINX ingress controller installed successfully. "
            f"Service endpoint: {endpoint}"
        )
    else:
        warning(
            "⚠️  Ingress-nginx installation finished, but the controller could not "
            "be detected. Please verify the installation manually."
        )
    return status
