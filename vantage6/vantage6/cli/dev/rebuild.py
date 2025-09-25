import subprocess
import sys

import click

from vantage6.common import error, info

from vantage6.cli.dev.common import check_devspace_installed


@click.command()
@click.option("--only-server", is_flag=True, help="Rebuild the server image.")
@click.option("--only-node", is_flag=True, help="Rebuild the node image.")
@click.option("--only-store", is_flag=True, help="Rebuild the store image.")
@click.option("--only-ui", is_flag=True, help="Rebuild the ui image.")
def cli_rebuild_dev_env(
    only_server: bool, only_node: bool, only_store: bool, only_ui: bool
):
    """Rebuild Docker images for your development environment."""
    check_devspace_installed()

    try:
        info("🔄 Rebuilding development environment with devspace...")
        cmd = ["devspace", "run", "rebuild"]

        if only_server:
            cmd.append("--server")
        if only_node:
            cmd.append("--node")
        if only_store:
            cmd.append("--store")
        if only_ui:
            cmd.append("--ui")

        subprocess.run(cmd, check=True, capture_output=False)
        info("✅ Development environment rebuilt successfully!")
    except subprocess.CalledProcessError as e:
        error(f"❌ Error rebuilding development environment: {e}")
        sys.exit(e.returncode)
