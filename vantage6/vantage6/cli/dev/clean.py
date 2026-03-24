import subprocess
import sys

import click

from vantage6.common import error, info

from vantage6.cli.dev.common import check_devspace_installed


@click.command()
def cli_clean_dev_env():
    """
    Stops and cleans up the development environment.

    Removes the kubernetes resources and local data (e.g. tasks data, database data).
    This is useful when you want to start from scratch.
    """
    check_devspace_installed()

    try:
        info("🧹 Cleaning development environment with devspace...")
        cmd = ["devspace", "run", "purge"]
        subprocess.run(cmd, check=True, capture_output=False)
        info("✅ Development environment cleaned successfully!")
    except subprocess.CalledProcessError as e:
        error(f"❌ Error cleaning development environment: {e}")
        sys.exit(e.returncode)
