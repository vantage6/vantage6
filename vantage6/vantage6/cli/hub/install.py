import os
import sys
from typing import Optional

import click
import requests

from vantage6.common import error, info, warning

from vantage6.cli.auth.install import check_and_install_keycloak_operator
from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config


def _get_latest_cert_manager_version() -> str:
    """
    Get the latest cert-manager release tag from GitHub.

    Raises a RuntimeError if the lookup fails, so that the caller can instruct
    the user to provide the version explicitly.
    """
    github_api_url = (
        "https://api.github.com/repos/cert-manager/cert-manager/releases/latest"
    )

    headers = {"Accept": "application/vnd.github.v3+json"}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        response = requests.get(github_api_url, timeout=5, headers=headers)
        response.raise_for_status()
        release_data = response.json()
        version = release_data.get("tag_name")
        if not version:
            raise RuntimeError(
                "No tag_name found in cert-manager GitHub releases response."
            )
        return version
    except Exception as exc:  # pragma: no cover - best-effort helper
        raise RuntimeError(
            f"Failed to fetch latest cert-manager version from GitHub: {exc!r}"
        ) from exc


def _check_cert_manager_crds_installed(k8s_config: KubernetesConfig) -> bool:
    """
    Check if the cert-manager Certificate CRD is already installed.

    We only check for the `certificates.cert-manager.io` CRD here, as that is what
    the hub chart requires to create Certificate resources.
    """
    try:
        result = run_kubectl_command(
            ["get", "crd", "certificates.cert-manager.io"],
            k8s_config=k8s_config,
            check=False,
            use_k8s_config_namespace=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_and_install_cert_manager_crds(
    k8s_config: KubernetesConfig,
    version: Optional[str] = None,
) -> None:
    """
    Ensure that cert-manager CRDs are installed in the cluster.

    This installs only the CRDs required for the hub chart (in particular
    `certificates.cert-manager.io`) so that Certificate resources can be created.
    """
    try:
        if _check_cert_manager_crds_installed(k8s_config):
            info("✅ cert-manager CRDs are already installed.")
            return

        info("⚠️  cert-manager CRDs are not installed.")
        info("Installing cert-manager CRDs...")

        if version is None:
            try:
                version = _get_latest_cert_manager_version()
            except RuntimeError as exc:
                error(str(exc))
                error(
                    "Please re-run 'v6 hub install' with the "
                    "--cert-manager-version flag to specify the cert-manager "
                    "version explicitly (for example: 'v1.15.3')."
                )
                sys.exit(1)

        crds_url = (
            "https://github.com/cert-manager/cert-manager/releases/download/"
            f"{version}/cert-manager.crds.yaml"
        )
        run_kubectl_command(
            ["apply", "-f", crds_url],
            k8s_config=k8s_config,
        )
        info("✅ cert-manager CRDs installed successfully.")
    except Exception as exc:  # pragma: no cover - best-effort helper
        warning(f"⚠️  Could not ensure cert-manager CRDs are installed: {exc}")
        warning(
            "If hub installation fails due to missing Certificate CRDs, please run "
            "'v6 hub install' or install cert-manager manually and try again."
        )


def cert_manager_seems_installed(k8s_config: KubernetesConfig) -> bool:
    """
    Heuristically check whether cert-manager (or an equivalent controller)
    appears to be installed.

    We do not attempt to install cert-manager automatically from the hub CLI
    because clusters may already have a controller that owns the
    'webhook.cert-manager.io' ValidatingWebhookConfiguration (for example via a
    platform component such as 'admissionsenforcer').
    """
    # Primary check: a cert-manager deployment in the cert-manager namespace.
    try:
        result = run_kubectl_command(
            ["get", "deployment", "cert-manager", "-n", "cert-manager"],
            k8s_config=k8s_config,
            check=False,
            # intentionally not using the namespace from the Kubernetes configuration
            use_k8s_config_namespace=False,
        )
        if result.returncode == 0:
            return True
    except Exception:
        pass

    # Fallback: presence of the webhook configuration is a strong indicator
    # that something is already managing cert-manager-style webhooks.
    try:
        result = run_kubectl_command(
            ["get", "validatingwebhookconfiguration", "webhook.cert-manager.io"],
            k8s_config=k8s_config,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--cert-manager-version",
    default=None,
    help=(
        "cert-manager version tag to use for CRDs. "
        "If omitted, the latest release is looked up from GitHub; "
        "if that lookup fails, you will be asked to provide this flag explicitly."
    ),
)
def cli_hub_install(
    context: str | None,
    namespace: str | None,
    cert_manager_version: str | None,
) -> None:
    """
    Install prerequisites for running a vantage6 hub.

    This command installs:

    - cert-manager CRDs (so that Certificate resources can be created)
    - the Keycloak operator (and its CRDs), reused from `v6 auth install-keycloak`
    """
    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # Ensure cert-manager CRDs are present.
    check_and_install_cert_manager_crds(k8s_config, version=cert_manager_version)

    # Ensure Keycloak operator (and its CRDs) are present.
    try:
        check_and_install_keycloak_operator(k8s_config)
    except SystemExit as exc:
        # Bubble up a clear error instead of a silent exit.
        error(
            "Failed to install the Keycloak operator while running 'v6 hub install'. "
            "Please inspect the logs above and try again."
        )
        raise exc
