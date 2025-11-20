import re
import subprocess
import time

import click

from vantage6.common import error, info, warning
from vantage6.common.globals import LOCALHOST, InstanceType, Ports

from vantage6.cli.common.decorator import click_insert_context
from vantage6.cli.common.start import (
    helm_install,
    prestart_checks,
)
from vantage6.cli.context.auth import AuthContext
from vantage6.cli.globals import ChartName
from vantage6.cli.k8s_config import KubernetesConfig, select_k8s_config
from vantage6.cli.utils import validate_input_cmd_args


@click.command()
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option("--ip", default=None, help="IP address to listen on")
@click.option(
    "-p",
    "--port",
    default=None,
    type=int,
    help="Port to listen on for the auth service",
)
@click.option(
    "--attach/--detach",
    default=False,
    help="Print server logs to the console after start",
)
@click.option("--local-chart-dir", default=None, help="Local chart directory to use")
@click.option("--chart-version", default=None, help="Chart version to use")
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
@click_insert_context(
    type_=InstanceType.AUTH,
    include_name=True,
    include_system_folders=True,
    sandbox_param="sandbox",
)
def cli_auth_start(
    ctx: AuthContext,
    name: str,
    system_folders: bool,
    context: str,
    namespace: str,
    ip: str,
    port: int,
    attach: bool,
    local_chart_dir: str,
    chart_version: str | None,
) -> None:
    """
    Start the auth service.
    """
    info("Starting authentication service...")

    prestart_checks(ctx, InstanceType.AUTH, name, system_folders)

    k8s_config = select_k8s_config(context=context, namespace=namespace)

    # TODO: re-enable when we save the auth logs
    # create_directory_if_not_exists(ctx.log_dir)

    info("Starting auth service. This may take a few minutes...")
    helm_install(
        release_name=ctx.helm_release_name,
        chart_name=ChartName.AUTH,
        values_file=ctx.config_file,
        k8s_config=k8s_config,
        local_chart_dir=local_chart_dir,
        chart_version=chart_version,
    )

    # port forward for auth service
    info("Port forwarding for auth service")
    start_port_forward(
        service_name=f"{ctx.helm_release_name}-keycloak",
        service_port=Ports.HTTP.value,
        port=port or Ports.DEV_AUTH.value,
        ip=ip,
        k8s_config=k8s_config,
    )

    if attach:
        warning("Attaching to auth logs is not supported yet.")
        # attach_logs(
        #     name,
        #     instance_type=InstanceType.AUTH,
        #     infra_component=InfraComponentName.AUTH,
        #     system_folders=system_folders,
        #     context=context,
        #     namespace=namespace,
        #     is_sandbox=ctx.is_sandbox,
        # )


def start_port_forward(
    service_name: str,
    service_port: int,
    port: int,
    k8s_config: KubernetesConfig,
    ip: str = LOCALHOST,
) -> None:
    """
    Port forward a kubernetes service.

    Parameters
    ----------
    service_name : str
        The name of the Kubernetes service to port forward.
    service_port : int
        The port on the service to forward.
    port : int
        The port to listen on.
    ip : str
        The IP address to listen on. Defaults to localhost.
    context : str | None
        The Kubernetes context to use.
    namespace : str | None
        The Kubernetes namespace to use.
    """
    # Input validation
    validate_input_cmd_args(service_name, "service name")
    if not isinstance(service_port, int) or service_port <= 0:
        error(f"Invalid service port: {service_port}. Must be a positive integer.")
        return

    if not isinstance(port, int) or port <= 0:
        error(f"Invalid local port: {port}. Must be a positive integer.")
        return

    if ip and not re.match(
        r"^(localhost|[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})$", ip
    ):
        error(f"Invalid IP address: {ip}. Must be a valid IPv4 address or 'localhost'.")
        return

    if k8s_config.context:
        validate_input_cmd_args(k8s_config.context, "context name", allow_none=True)
    if k8s_config.namespace:
        validate_input_cmd_args(k8s_config.namespace, "namespace name", allow_none=True)

    # Check if the service is ready before starting port forwarding
    info(f"Waiting for service '{service_name}' to become ready...")
    start_time = time.time()
    timeout = 300  # seconds
    while time.time() - start_time < timeout:
        try:
            command = [
                "kubectl",
                "get",
                "endpoints",
                service_name,
                "-o",
                "jsonpath={.subsets[*].addresses[*].ip}",
            ]

            if k8s_config.context:
                command.extend(["--context", k8s_config.context])

            if k8s_config.namespace:
                command.extend(["--namespace", k8s_config.namespace])

            result = subprocess.check_output(command).decode().strip()

            if result:
                info(f"Service '{service_name}' is ready.")
                break
        except subprocess.CalledProcessError:
            pass  # ignore and retry

        time.sleep(2)
    else:
        error(
            f"Timeout: Service '{service_name}' has no ready endpoints after {timeout} "
            "seconds."
        )
        return

    # Create the port forwarding command
    if not ip:
        ip = LOCALHOST

    command = [
        "kubectl",
        "port-forward",
        "--address",
        ip,
        f"service/{service_name}",
        f"{port}:{service_port}",
    ]

    if k8s_config.context:
        command.extend(["--context", k8s_config.context])

    if k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])

    # Start the port forwarding process
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            start_new_session=True,  # Start in new session to detach from parent
        )

        # Give the process a moment to start and check if it's still running
        time.sleep(1)
        if process.poll() is not None:
            # Process has already terminated
            e = process.stderr.read().decode() if process.stderr else "Unknown error"
            error(f"Failed to start port forwarding: {e}")
            return

        info(
            f"Port forwarding started: {ip}:{port} -> {service_name}:{service_port} "
            f"(PID: {str(process.pid)})"
        )
        return
    except Exception as e:
        error(f"Failed to start port forwarding: {e}")
        return
