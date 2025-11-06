import click

from vantage6.common import info, warning
from vantage6.common.globals import (
    DEFAULT_DOCKER_REGISTRY,
    DEFAULT_NODE_IMAGE,
    DEFAULT_NODE_IMAGE_WO_TAG,
    InstanceType,
)

from vantage6.cli import __version__
from vantage6.cli.common.attach import attach_logs
from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.common.utils import (
    create_directory_if_not_exists,
    select_context_and_namespace,
)
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import ChartName, InfraComponentName
from vantage6.cli.node.common import create_client


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the node",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
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
) -> None:
    """
    Start the node.
    """
    info("Starting node...")

    prestart_checks(ctx, InstanceType.NODE, name, system_folders)

    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    create_directory_if_not_exists(ctx.log_dir)
    create_directory_if_not_exists(ctx.data_dir)

    # Determine image-name. First we check if the image is set in the config file.
    # If so, we use it. Otherwise, we use the same version as the server.
    if custom_image := ctx.config.get("node", {}).get("image"):
        image = custom_image
    else:
        # if no custom image is specified, find the server version and use
        # the latest images from that minor version
        client = create_client(ctx, use_sandbox_port=ctx.is_sandbox)
        major_minor = None
        try:
            # try to get server version, skip if can't get a connection
            version = client.util.get_server_version(attempts_on_timeout=3)["version"]
            major_minor = ".".join(version.split(".")[:2])
            image = (
                f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE_WO_TAG}:{major_minor}"
            )
        except Exception:
            warning("Could not determine server version. Using default node image")

        if major_minor and not __version__.startswith(major_minor):
            warning(
                "Version mismatch between CLI and server/node. CLI is running on "
                f"version {__version__}, while node and server are on version "
                f"{major_minor}. This might cause unexpected issues; changing to "
                f"{major_minor}.<latest> is recommended."
            )

    # fail safe, in case no custom image is specified and we can't get the
    # server version
    if not image:
        image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE}"

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.NODE,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
        local_chart_dir=local_chart_dir,
        custom_values=[f"node.image={image}"],
    )

    if attach:
        attach_logs(
            name,
            instance_type=InstanceType.NODE,
            infra_component=InfraComponentName.NODE,
            system_folders=system_folders,
            context=context,
            namespace=namespace,
            is_sandbox=ctx.is_sandbox,
        )
