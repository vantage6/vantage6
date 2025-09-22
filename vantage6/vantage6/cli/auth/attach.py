import click

from vantage6.common import error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    attach_logs,
    find_running_service_names,
    select_context_and_namespace,
    select_running_service,
)


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "-n", "--name", default=None, help="Name of the auth service to attach to"
)
def cli_auth_attach(context: str, namespace: str, name: str) -> None:
    """
    Show the server logs in the current console.
    """
    info("Attaching to auth logs...")

    context, namespace = select_context_and_namespace(
        context=context,
        namespace=namespace,
    )

    running_services = find_running_service_names(
        instance_type=InstanceType.AUTH,
        only_system_folders=False,
        only_user_folders=False,
        context=context,
        namespace=namespace,
    )

    if not running_services:
        error("No running auth services found.")
        return

    if name:
        # search for a running auth service started up either in user or system folders
        svc_name_options = [
            f"vantage6-{name}-user-auth",
            f"vantage6-{name}-system-auth",
        ]
        helm_name = next(
            (svc for svc in svc_name_options if svc in running_services), None
        )
        if not helm_name:
            error(f"No running auth service found for {name}.")
            return
    else:
        helm_name = select_running_service(running_services, InstanceType.AUTH)

    attach_logs(
        f"app.kubernetes.io/instance={helm_name}",
    )
