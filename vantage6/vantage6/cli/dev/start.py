import subprocess
import sys

import click

from vantage6.common import error, info, warning

from vantage6.cli.dev.common import check_devspace_installed
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config


@click.command()
@click.option(
    "--with-prometheus", is_flag=True, default=False, help="Enable Prometheus"
)
@click.option(
    "--no-local-auth",
    is_flag=True,
    default=False,
    help="Don't create local Keycloak service",
)
@click.option(
    "--no-populate",
    "populate",
    is_flag=True,
    flag_value=False,
    help="Do not populate the development environment with example data. Only applied "
    "this time the development environment is started, or after it is cleaned.",
)
@click.option(
    "--populate",
    "populate",
    is_flag=True,
    flag_value=True,
    default=True,
    help="Populate the development environment with example data. Only applied the "
    "first time the development environment is started, or after it is cleaned.",
)
@click.option(
    "--repopulate",
    is_flag=True,
    default=False,
    help="Repopulate the development environment with example data. This will delete "
    "all existing data and repopulate the development environment with example data. "
    "This has a similar effect to running `v6 dev clean` and then "
    "`v6 dev start --populate`.",
)
def cli_start_dev_env(
    with_prometheus: bool, no_local_auth: bool, populate: bool, repopulate: bool
):
    """Start the development environment using devspace."""
    check_devspace_installed()

    if no_local_auth and with_prometheus:
        error("❌ Cannot use --no-local-auth and --with-prometheus together.")
        sys.exit(1)

    # Check if Keycloak operator is installed (only if local auth is enabled)
    if not no_local_auth:
        _install_keycloak_operator()

    try:
        info("🚀 Starting development environment with devspace...")

        # Build the devspace command
        cmd = ["devspace", "run", "start-dev"]

        if with_prometheus:
            cmd.extend(["--profile", "with-prometheus"])
        if no_local_auth:
            cmd.extend(["--profile", "no-local-auth"])

        if repopulate:
            cmd.append("--repopulate")
        elif populate:
            cmd.append("--populate")
        else:
            cmd.append("--no-populate")

        # Run the devspace command
        result = subprocess.run(cmd, check=True, capture_output=False)

        if result.returncode == 0:
            info("✅ Development environment started successfully!")
        else:
            error("❌ Failed to start development environment.")
            sys.exit(result.returncode)

    except subprocess.CalledProcessError as e:
        error(f"❌ Error running devspace: {e}")
        info("Note that you need to run this command from the vantage6 root directory.")
        sys.exit(e.returncode)
    except Exception as e:
        error(f"❌ Unexpected error: {e}")
        sys.exit(1)


def _install_keycloak_operator():
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
    except Exception as e:
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
    except Exception:
        return False
