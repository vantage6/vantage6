import subprocess
import sys
import time

import click
from kubernetes.config.config_exception import ConfigException
from packaging.version import InvalidVersion, Version

from vantage6.common import error, info, warning

from vantage6.cli.common.k8s_utils import run_kubectl_command
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config

SUPPORTED_KEYCLOAK_OPERATOR_VERSION = "26.6.2"
KEYCLOAK_CLIENT_CRDS_MIN_VERSION = (26, 7, 0)


def _parse_operator_version(version: str) -> tuple[int, int, int]:
    """Validate and convert a Keycloak operator version to a comparable tuple."""
    try:
        version = Version(version)
    except InvalidVersion:
        raise click.BadParameter(
            "must use semantic version format 'major.minor.patch'",
            param_hint="--operator-version",
        )
    return (version.major, version.minor, version.micro)


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace for the operator")
@click.option(
    "--operator-version",
    default=SUPPORTED_KEYCLOAK_OPERATOR_VERSION,
    show_default=True,
    help=(
        "Keycloak Operator version to install. Overriding the default opts into an "
        "operator release that may not have been compatibility-tested with vantage6."
    ),
)
@click.option(
    "--skip-crds/--no-skip-crds",
    default=False,
    help="Skip installing custom resource definitions (CRDs)",
)
def cli_auth_install_operator(
    context: str | None,
    namespace: str | None,
    operator_version: str,
    skip_crds: bool,
) -> None:
    """
    Install the Keycloak Operator and its CRDs in the Kubernetes cluster.

    This command installs the Keycloak Operator which is required to manage
    Keycloak instances using Custom Resources. This installation is done according to
    the docs in
    https://www.keycloak.org/operator/installation#_installing_by_using_kubectl_without_operator_lifecycle_manager
    """
    parsed_operator_version = _parse_operator_version(operator_version)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # Base URL for Keycloak Operator manifests
    base_url = (
        "https://raw.githubusercontent.com/keycloak/keycloak-k8s-resources/"
        f"{operator_version}/kubernetes/"
    )

    # Install custom resource definitions (CRDs)
    crd_files_to_install = [
        "keycloaks.k8s.keycloak.org-v1.yml",
        "keycloakrealmimports.k8s.keycloak.org-v1.yml",
    ]
    if parsed_operator_version >= KEYCLOAK_CLIENT_CRDS_MIN_VERSION:
        crd_files_to_install.extend(
            [
                "keycloakoidcclients.k8s.keycloak.org-v1.yml",
                "keycloaksamlclients.k8s.keycloak.org-v1.yml",
            ]
        )
    if not skip_crds:
        info("Installing Keycloak CRDs...")
        for crd_file in crd_files_to_install:
            crd_url = f"{base_url}/{crd_file}"
            run_kubectl_command(
                ["apply", "-f", crd_url],
                k8s_config,
            )
        info("CRDs installed successfully.")

    # Install the operator only after all CRDs required by this version are available.
    run_kubectl_command(
        ["apply", "-f", f"{base_url}/kubernetes.yml"],
        k8s_config,
    )

    # Adapt the clusterrolebinding to use the correct namespace (see
    # https://www.keycloak.org/operator/installation)
    run_kubectl_command(
        [
            "patch",
            "clusterrolebinding",
            "keycloak-operator-clusterrole-binding",
            "--type=json",
            (
                '-p=[{"op": "replace", "path": "/subjects/0/namespace", "value":"'
                'custom-namespace"}]'
            ),
        ],
        k8s_config=k8s_config,
    )
    info("Clusterrolebinding adapted to use the correct namespace.")

    run_kubectl_command(
        [
            "rollout",
            "restart",
            "Deployment/keycloak-operator",
        ],
        k8s_config=k8s_config,
    )
    info("Keycloak Operator rolled out successfully.")

    # Wait for operator to be ready
    info("Waiting for Keycloak Operator to become ready...")
    _wait_for_operator_ready(k8s_config.namespace, k8s_config, timeout=300)

    info(
        "Keycloak Operator installed successfully in namespace "
        f"'{k8s_config.namespace}'."
    )


def _wait_for_operator_ready(
    namespace: str,
    k8s_config,
    timeout: int = 300,
) -> None:
    """
    Wait for the Keycloak Operator deployment to become ready.

    Parameters
    ----------
    namespace : str
        The namespace where the operator is installed.
    k8s_config
        Kubernetes configuration object.
    timeout : int
        Maximum time to wait in seconds (default: 300).
    """
    start_time = time.time()
    deployment_name = "keycloak-operator"

    while (time.time() - start_time) < timeout:
        try:
            command = [
                "kubectl",
                "get",
                "deployment",
                deployment_name,
                "-n",
                namespace,
                "-o",
                'jsonpath={.status.conditions[?(@.type=="Available")].status}',
            ]

            if k8s_config.context:
                command.extend(["--context", k8s_config.context])

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.stdout.strip() == "True":
                info("Keycloak Operator is ready.")
                return

        except (OSError, subprocess.SubprocessError) as e:
            warning(f"Error checking operator status: {e}")

        time.sleep(5)

    error(f"Timeout: Keycloak Operator did not become ready within {timeout} seconds.")
    warning(
        "You can check the operator status manually with: "
        f"kubectl get deployment keycloak-operator -n {namespace}"
    )
    raise click.ClickException(
        f"Keycloak Operator did not become ready within {timeout} seconds."
    )


def check_and_install_keycloak_operator(k8s_config: KubernetesConfig):
    try:
        k8s_config = select_k8s_config(context=None, namespace=None)
        if not _check_keycloak_operator_installed(k8s_config):
            warning("⚠️  Keycloak operator is not installed.")
            info("Installing Keycloak operator...")
            cmd = ["v6", "auth", "install-keycloak"]
            if k8s_config.context:
                cmd.extend(["--context", k8s_config.context])
            if k8s_config.namespace:
                cmd.extend(["--namespace", k8s_config.namespace])

            result = subprocess.run(cmd, check=False)
            if result.returncode != 0:
                error("❌ Failed to install Keycloak operator.")
                error("Please run 'v6 auth install-keycloak' manually and try again.")
                sys.exit(1)
            info("✅ Keycloak operator installed successfully.")
        else:
            info("✅ Keycloak operator is already installed.")
    except (ConfigException, OSError, subprocess.SubprocessError) as e:
        warning(f"⚠️  Could not check Keycloak operator status: {e}")
        warning(
            "Continuing anyway. If Keycloak fails to start, run 'v6 auth "
            "install-keycloak' manually."
        )


def _check_keycloak_operator_installed(k8s_config: KubernetesConfig) -> bool:
    """
    Check if the Keycloak operator is already installed.

    Parameters
    ----------
    k8s_config
        Kubernetes configuration object.

    Returns
    -------
    bool
        True if the operator is installed, False otherwise.
    """
    try:
        cmd = ["kubectl", "get", "deployment", "keycloak-operator"]
        if k8s_config.context:
            cmd.extend(["--context", k8s_config.context])
        if k8s_config.namespace:
            cmd.extend(["--namespace", k8s_config.namespace])

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )
        return result.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False
