import os
import subprocess
import time

import click
import requests

from vantage6.common import error, info, warning

from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config


def _get_latest_keycloak_version() -> str:
    """
    Get the latest Keycloak Operator version from GitHub releases.

    Returns
    -------
    str
        The latest version found in the Keycloak Github releases.
    """
    github_api_url = "https://api.github.com/repos/keycloak/keycloak/releases/latest"

    # Prepare headers with optional GitHub token for authentication
    headers = {"Accept": "application/vnd.github.v3+json"}
    github_token = os.environ.get("GITHUB_TOKEN")
    if github_token:
        headers["Authorization"] = f"token {github_token}"

    try:
        response = requests.get(
            github_api_url,
            timeout=5,
            headers=headers,
        )
        response.raise_for_status()
        release_data = response.json()
        version = release_data.get("tag_name")
        if not version:
            error("No version found in the Keycloak Github releases.")
            info("Please specify a version manually using the --operator-version flag.")
            exit(1)
        # Remove 'v' prefix if present (e.g., "v24.0.0" -> "24.0.0")
        if version.startswith("v"):
            version = version[1:]
        return version
    except requests.HTTPError as e:
        if e.response.status_code == 403:
            error(
                "GitHub API rate limit exceeded. "
                "Set GITHUB_TOKEN environment variable to authenticate and increase rate limits, "
                "or specify a version manually using the --operator-version flag."
            )
        else:
            error(
                f"Failed to fetch latest Keycloak Operator version from GitHub: {e}. "
            )
        info("Please specify a version manually using the --operator-version flag.")
        exit(1)
    except (requests.RequestException, KeyError, ValueError) as e:
        error(f"Failed to fetch latest Keycloak Operator version from GitHub: {e}. ")
        info("Please specify a version manually using the --operator-version flag.")
        exit(1)


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace for the operator")
@click.option(
    "--operator-version",
    default=None,
    help="Keycloak Operator version to install (defaults to latest from GitHub)",
)
@click.option(
    "--skip-crds/--no-skip-crds",
    default=False,
    help="Skip installing custom resource definitions (CRDs)",
)
def cli_auth_install_operator(
    context: str | None,
    namespace: str | None,
    operator_version: str | None,
    skip_crds: bool,
) -> None:
    """
    Install the Keycloak Operator and its CRDs in the Kubernetes cluster.

    This command installs the Keycloak Operator which is required to manage
    Keycloak instances using Custom Resources. This installation is done according to
    the docs in
    https://www.keycloak.org/operator/installation#_installing_by_using_kubectl_without_operator_lifecycle_manager
    """
    # Get the latest version if not specified
    if operator_version is None:
        operator_version = _get_latest_keycloak_version()

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
        "kubernetes.yml",
    ]
    if not skip_crds:
        info("Installing Keycloak CRDs...")
        for crd_file in crd_files_to_install:
            crd_url = f"{base_url}/{crd_file}"
            _run_kubectl_command(
                ["kubectl", "apply", "-f", crd_url],
                k8s_config,
            )
        info("CRDs installed successfully.")

    # Adapt the clusterrolebinding to use the correct namespace (see
    # https://www.keycloak.org/operator/installation)
    _run_kubectl_command(
        [
            "kubectl",
            "patch",
            "clusterrolebinding",
            "keycloak-operator-clusterrole-binding",
            "--type=json",
            '-p=[{"op": "replace", "path": "/subjects/0/namespace", "value":"'
            'custom-namespace"}]',
        ],
        k8s_config=k8s_config,
    )
    info("Clusterrolebinding adapted to use the correct namespace.")

    _run_kubectl_command(
        [
            "kubectl",
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


def _run_kubectl_command(
    command: list[str],
    k8s_config: KubernetesConfig,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """
    Run a kubectl command with the appropriate context and namespace.

    Parameters
    ----------
    command : list[str]
        The kubectl command to run (without 'kubectl' prefix if already included).
    k8s_config: KubernetesConfig
        Kubernetes configuration object with context and namespace.
    check : bool
        Whether to raise an exception on non-zero exit code.

    Returns
    -------
    subprocess.CompletedProcess
        The result of the subprocess call.
    """
    # Add context if specified
    if k8s_config.context:
        command.extend(["--context", k8s_config.context])

    if k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])

    info(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(
            command,
            check=check,
            capture_output=True,
            text=True,
        )
        if result.stdout:
            info(result.stdout.strip())
        return result
    except subprocess.CalledProcessError as e:
        error(f"Command failed: {' '.join(command)}")
        if e.stderr:
            error(f"Error: {e.stderr}")
        if check:
            raise
        return e


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

    while time.time() - start_time < timeout:
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

        except Exception as e:
            warning(f"Error checking operator status: {e}")

        time.sleep(5)

    error(f"Timeout: Keycloak Operator did not become ready within {timeout} seconds.")
    warning(
        "You can check the operator status manually with: "
        f"kubectl get deployment keycloak-operator -n {namespace}"
    )
