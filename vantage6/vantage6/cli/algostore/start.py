import click

from vantage6.common import info
from vantage6.common.globals import (
    APPNAME,
    DEFAULT_ALGO_STORE_IMAGE,
    InstanceType,
    Ports,
)
from vantage6.cli.common.start import (
    attach_logs,
    check_for_start,
    get_image,
    mount_config_file,
    mount_database,
    mount_source,
    pull_infra_image,
)
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.cli.common.decorator import click_insert_context


@click.command()
@click.option("--ip", default=None, help="IP address to listen on")
@click.option("-p", "--port", default=None, type=int, help="Port to listen on")
@click.option("-i", "--image", default=None, help="Algorithm store Docker image to use")
@click.option(
    "--keep/--auto-remove",
    default=False,
    help="Keep image after algorithm store has been stopped. Useful " "for debugging",
)
@click.option(
    "--mount-src",
    default="",
    help="Override vantage6 source code in container with the source"
    " code in this path",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click_insert_context(InstanceType.ALGORITHM_STORE)
def cli_algo_store_start(
    ctx: AlgorithmStoreContext,
    ip: str,
    port: int,
    image: str,
    keep: bool,
    mount_src: str,
    attach: bool,
) -> None:
    """
    Start the algorithm store server.
    """
    info("Starting algorithm store...")
    docker_client = check_for_start(ctx, InstanceType.ALGORITHM_STORE)

    image = get_image(image, ctx, "algorithm-store", DEFAULT_ALGO_STORE_IMAGE)

    info("Pulling algorithm store image...")
    pull_infra_image(docker_client, image, InstanceType.ALGORITHM_STORE)

    config_file = "/mnt/config.yaml"
    mounts = mount_config_file(ctx, config_file)

    src_mount = mount_source(mount_src)
    if src_mount:
        mounts.append(src_mount)

    mount, environment_vars = mount_database(ctx, InstanceType.ALGORITHM_STORE)
    if mount:
        mounts.append(mount)

    # The `ip` and `port` refer here to the ip and port within the container.
    # So we do not really care that is it listening on all interfaces.
    internal_port = 5000
    cmd = (
        f"uwsgi --http :{internal_port} --gevent 1000 --http-websockets "
        "--master --callable app --disable-logging "
        "--wsgi-file /vantage6/vantage6-algorithm-store/vantage6/algorithm"
        f"/store/wsgi.py --pyargv {config_file}"
    )
    info(cmd)

    info("Run Docker container")
    port_ = str(port or ctx.config["port"] or Ports.DEV_ALGO_STORE.value)
    container = docker_client.containers.run(
        image,
        command=cmd,
        mounts=mounts,
        detach=True,
        labels={
            f"{APPNAME}-type": InstanceType.ALGORITHM_STORE,
            "name": ctx.config_file_name,
        },
        environment=environment_vars,
        ports={f"{internal_port}/tcp": (ip, port_)},
        name=ctx.docker_container_name,
        auto_remove=not keep,
        tty=True,
    )

    info(f"Success! container id = {container.id}")

    if attach:
        attach_logs(container, InstanceType.ALGORITHM_STORE)
