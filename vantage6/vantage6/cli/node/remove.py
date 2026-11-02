from pathlib import Path
from shutil import rmtree

import click
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import info, warning
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.remove import execute_remove
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config
from vantage6.cli.node.common.private_key import (
    delete_private_key_secret,
    private_key_secret_name,
)


@click.command()
@click.option(
    "-f", "--force", type=bool, flag_value=True, help="Don't ask for confirmation"
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    type_=InstanceType.NODE,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_node_remove(
    ctx: NodeContext,
    name: str,
    system_folders: bool,
    force: bool,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Delete a node permanently.

    Remove the configuration file, log file, and kubernetes resources attached to
    the node, including the Kubernetes secret with the node's private key.
    """

    execute_remove(
        ctx, InstanceType.NODE, InfraComponentName.NODE, name, system_folders, force
    )

    # remove the folder: if it hasn't been started yet this won't exist...
    if Path.exists(ctx.config_dir / name):
        rmtree(ctx.config_dir / name)

    _remove_private_key_secret(ctx, context, namespace)


def _remove_private_key_secret(
    ctx: NodeContext, context: str | None, namespace: str | None
) -> None:
    """Delete the Kubernetes secret that holds the node's private key, if any."""
    secret_name = private_key_secret_name(ctx)
    k8s_config = select_k8s_config(context=context, namespace=namespace)
    try:
        deleted = delete_private_key_secret(ctx, k8s_config)
    except (RuntimeError, ApiException, HTTPError) as exc:
        warning(
            f"Could not delete the private key secret '{secret_name}' in namespace "
            f"'{k8s_config.namespace}'. Please delete it manually."
        )
        warning(str(exc))
        return
    if deleted:
        info(f"Removed private key secret '{secret_name}'")
