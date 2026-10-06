import os
import sys
from pathlib import Path

import click
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import debug, error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.context.node import NodeContext
from vantage6.cli.k8s_config import select_k8s_config
from vantage6.cli.node.common.private_key import (
    private_key_secret_name,
    read_private_key_secret,
)


@click.command()
@click.option(
    "--to-file",
    "to_file",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Write the private key to this file instead of printing it",
)
@click.option(
    "--overwrite",
    is_flag=True,
    default=False,
    help="Overwrite the file given with --to-file if it exists",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    InstanceType.NODE,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_node_get_private_key(
    ctx: NodeContext,
    name: str,
    system_folders: bool,
    to_file: Path | None,
    overwrite: bool,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Get the node's private key from its Kubernetes secret

    Use this to give the organization's private key to the Python client or UI, e.g.
    to decrypt results. The key is printed, or written to a file that only you can
    read if --to-file is given.
    """
    k8s_config = select_k8s_config(context=context, namespace=namespace)
    try:
        pem = read_private_key_secret(ctx, k8s_config)
    except (RuntimeError, ApiException, HTTPError) as e:
        error("Could not read the private key secret from Kubernetes!")
        debug(e)
        sys.exit(1)

    if pem is None:
        error(
            f"Private key secret '{private_key_secret_name(ctx)}' does not exist in "
            f"namespace '{k8s_config.namespace}'."
        )
        sys.exit(1)

    if to_file is None:
        click.echo(pem.decode(), nl=False)
        return

    if to_file.exists() and not overwrite:
        error(f"'{to_file}' already exists. Use --overwrite to replace it.")
        sys.exit(1)

    # create the file owner-readable only, so other users cannot read the key
    fd = os.open(to_file, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(pem)
    os.chmod(to_file, 0o600)
    info(f"Private key written to '{to_file}'")
