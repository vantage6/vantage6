import subprocess
import sys

import click

from vantage6.common import error, info

from vantage6.cli.dev.common import check_devspace_installed


@click.command()
def cli_start_dev_env():
    """Start the development environment using devspace."""
    check_devspace_installed()

    try:
        info("🚀 Starting development environment with devspace...")

        # Build the devspace command
        cmd = ["devspace", "run", "start-dev"]

        # Run the devspace command
        result = subprocess.run(cmd, check=True, capture_output=False)

        if result.returncode == 0:
            info("✅ Development environment started successfully!")
        else:
            error("❌ Failed to start development environment.")
            sys.exit(result.returncode)

    except subprocess.CalledProcessError as e:
        error(f"❌ Error running devspace: {e}")
        sys.exit(e.returncode)
    except Exception as e:
        error(f"❌ Unexpected error: {e}")
        sys.exit(1)
