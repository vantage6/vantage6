import click
import requests

from vantage6.common import info, warning
from vantage6.common.globals import (
    DEFAULT_NODE_IMAGE,
    DEFAULT_NODE_IMAGE_WO_TAG,
    InstanceType,
)

from vantage6.cli import __version__
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.utils import create_directory_if_not_exists
from vantage6.cli.context.node import NodeContext
from vantage6.cli.deployment import get_node_deployment
from vantage6.cli.node.common import create_client


@click.command()
@click.option(
    "--context", default=None, help="Kubernetes context to use (Kubernetes nodes)"
)
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use (Kubernetes nodes)",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the node",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--chart-version", default=None, help="Chart version to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    InstanceType.NODE,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_node_start(
    ctx: NodeContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    attach: bool,
    local_chart_dir: str,
    chart_version: str | None,
) -> None:
    """
    Start the node.
    """
    info("Starting node...")

    deployment = get_node_deployment(
        ctx,
        name=name,
        system_folders=system_folders,
        context=context,
        namespace=namespace,
        local_chart_dir=local_chart_dir,
        chart_version=chart_version,
    )
    deployment.prestart_checks()

    create_directory_if_not_exists(ctx.log_dir)
    create_directory_if_not_exists(ctx.data_dir)

    image = resolve_node_image(ctx)
    deployment.start(image)

    if attach:
        deployment.attach_logs()


def resolve_node_image(ctx: NodeContext) -> str:
    """
    The image set in the node configuration, otherwise the latest node image of the
    minor version HQ runs.
    """
    if custom_image := ctx.config.get("node", {}).get("image"):
        return custom_image

    image = None
    client = create_client(ctx, use_sandbox_port=ctx.is_sandbox)
    major_minor = None
    try:
        # try to get HQ version, skip if can't get a connection
        version = client.util.get_hq_version(attempts_on_timeout=3)["version"]
        major_minor = ".".join(version.split(".")[:2])
        image = f"{DEFAULT_NODE_IMAGE_WO_TAG}:{major_minor}"
    except (requests.RequestException, KeyError):
        warning("Could not determine HQ version. Using default node image")

    if major_minor and not __version__.startswith(major_minor):
        warning(
            "Version mismatch between CLI and HQ/node. CLI is running on "
            f"version {__version__}, while node and HQ are on version "
            f"{major_minor}. This might cause unexpected issues; changing to "
            f"{major_minor}.<latest> is recommended."
        )

    # fail safe, in case we can't get the HQ version
    return image or DEFAULT_NODE_IMAGE
