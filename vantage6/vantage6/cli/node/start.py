import click

from vantage6.common import info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
    start_port_forward,
)
from vantage6.cli.common.utils import (
    attach_logs,
    create_directory_if_not_exists,
)
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import ChartName

from vantage6.node.globals import DEFAULT_PROXY_SERVER_PORT


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--attach/--detach",
    default=False,
    help="Show node logs on the current console after starting the node",
)
@click_insert_context(InstanceType.NODE, include_name=True, include_system_folders=True)
def cli_node_start(
    ctx: NodeContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    attach: bool,
) -> None:
    """
    Start the node.
    """
    info("Starting node...")

    prestart_checks(ctx, InstanceType.NODE, name, system_folders, context, namespace)

    create_directory_if_not_exists(ctx.log_dir)
    create_directory_if_not_exists(ctx.data_dir)

    # TODO issue #2256 - run same version node as server
    # # Determine image-name. First we check if the option --image has been used.
    # # Then we check if the image has been specified in the config file, and
    # # finally we use the default settings from the package.
    # if not image:
    #     custom_images: dict = ctx.config.get("images")
    #     if custom_images:
    #         image = custom_images.get("node")
    #     else:
    #         # if no custom image is specified, find the server version and use
    #         # the latest images from that minor version
    #         client = create_client(ctx)
    #         major_minor = None
    #         try:
    #             # try to get server version, skip if can't get a connection
    #             version = client.util.get_server_version(attempts_on_timeout=3)[
    #                 "version"
    #             ]
    #             major_minor = ".".join(version.split(".")[:2])
    #             image = (
    #                 f"{DEFAULT_DOCKER_REGISTRY}/"
    #                 f"{DEFAULT_NODE_IMAGE_WO_TAG}"
    #                 f":{major_minor}"
    #             )
    #         except Exception:
    #             warning("Could not determine server version. Using default node image")

    #         if major_minor and not __version__.startswith(major_minor):
    #             warning(
    #                 "Version mismatch between CLI and server/node. CLI is "
    #                 f"running on version {__version__}, while node and server "
    #                 f"are on version {major_minor}. This might cause "
    #                 f"unexpected issues; changing to {major_minor}.<latest> "
    #                 "is recommended."
    #             )

    #     # fail safe, in case no custom image is specified and we can't get the
    #     # server version
    #     if not image:
    #         image = f"{DEFAULT_DOCKER_REGISTRY}/{DEFAULT_NODE_IMAGE}"

    # info(f"Pulling latest node image '{image}'")
    # pull_infra_image(docker_client, image, InstanceType.NODE)

    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.NODE,
        values_file=ctx.config_file,
        context=context,
        namespace=namespace,
    )

    # start port forward for the node proxy server
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-node-service",
        service_port=ctx.config["node"].get("port", DEFAULT_PROXY_SERVER_PORT),
        port=ctx.config["node"].get("port", DEFAULT_PROXY_SERVER_PORT),
        context=context,
        namespace=namespace,
    )

    if attach:
        attach_logs("app=node")
