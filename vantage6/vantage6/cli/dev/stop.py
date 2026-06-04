import subprocess
import sys

import click

from vantage6.common import error, info

from vantage6.cli.dev.common import check_devspace_installed


@click.command()
def cli_stop_dev_env():
    """Stop the development environment."""
    check_devspace_installed()

    try:
        info("🛑 Stopping development environment with devspace...")
        cmd = ["devspace", "run", "stop-dev"]
        subprocess.run(cmd, check=True, capture_output=False)
        info("✅ Development environment stopped successfully!")
    except subprocess.CalledProcessError as e:
        error(f"❌ Error stopping development environment: {e}")
        sys.exit(e.returncode)
