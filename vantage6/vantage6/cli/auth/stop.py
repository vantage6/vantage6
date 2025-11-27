import subprocess

import click

from vantage6.cli.common.stop import execute_stop, helm_uninstall
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils import validate_input_cmd_args
from vantage6.common import error, info, warning
from vantage6.common.globals import InstanceType
from vantage6.common.kubernetes.utils import running_on_windows

@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Search for configuration in system folders instead of user folders. "
    "This is the default.",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    help="Search for configuration in the user folders instead of system folders.",
)
@click.option("--sandbox/--no-sandbox", "sandbox", default=False)
def cli_auth_stop(
    name: str,
    context: str,
    namespace: str,
    system_folders: bool,
    sandbox: bool,
):
    """
    Stop a running auth service.
    """
    execute_stop(
        stop_function=_stop_auth,
        instance_type=InstanceType.AUTH,
        infra_component=InfraComponentName.AUTH,
        stop_all=False,
        to_stop=name,
        namespace=namespace,
        context=context,
        system_folders=system_folders,
        is_sandbox=sandbox,
    )


def _stop_auth(auth_name: str, k8s_config: KubernetesConfig) -> None:
    info(f"Stopping auth {auth_name}...")

    # uninstall the helm release
    helm_uninstall(
        release_name=auth_name,
        k8s_config=k8s_config,
    )

    # stop the port forwarding for auth service
    stop_port_forward(
        service_name=f"{auth_name}-keycloak",
    )

    info(f"Auth {auth_name} stopped successfully.")


def stop_port_forward(service_name: str) -> None:
    """
    Stop the port forwarding process for a given service name.

    Parameters
    ----------
    service_name : str
        The name of the service whose port forwarding process should be terminated.
    """
    # Input validation
    validate_input_cmd_args(service_name, "service name")

    if running_on_windows():
        # Windows does not support pgrep/kill. Inspect netstat output instead.
        try:
            netstat = subprocess.run(
                ["netstat", "-aon"],
                check=True,
                text=True,
                capture_output=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            error(f"Failed to inspect netstat output: {exc}")
            return

        pid = None
        for line in netstat.stdout.splitlines():
            if ":8080" not in line or "LISTENING" not in line:
                continue
            columns = line.split()
            if columns and columns[-1].isdigit():
                pid = columns[-1]
                break

        if not pid:
            warning(
                f"No port forwarding process listening on 8080 found for '{service_name}'."
            )
            return
        elif int(pid) == 0:
            warning("Detected PID 0. This process will not be terminated.")
            return

        try:
            subprocess.run(["taskkill", "/PID", pid, "/F"], check=True)
            info(
                f"Terminated port forwarding process for service '{service_name}' "
                f"(PID: {pid})"
            )
        except (subprocess.CalledProcessError, FileNotFoundError) as exc:
            error(f"Failed to terminate port forwarding: {exc}")

        return

    try:
        # Find the process ID (PID) of the port forwarding command
        result = subprocess.run(
            ["pgrep", "-f", f"kubectl port-forward.*{service_name}"],
            check=True,
            text=True,
            capture_output=True,
        )
        print("not here")
        pids = result.stdout.strip().splitlines()

        if not pids:
            warning(f"No port forwarding process found for service '{service_name}'.")
            return

        for pid in pids:
            subprocess.run(["kill", "-9", pid], check=True)
            info(
                f"Terminated port forwarding process for service '{service_name}' "
                f"(PID: {pid})"
            )
    except subprocess.CalledProcessError as e:
        error(f"Failed to terminate port forwarding: {e}")
