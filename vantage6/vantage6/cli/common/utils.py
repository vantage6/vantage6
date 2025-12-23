import json
import subprocess
from pathlib import Path

import questionary as q
from kubernetes import client as k8s_client

from vantage6.common import error
from vantage6.common.globals import (
    APPNAME,
    SANDBOX_SUFFIX,
    InstanceType,
)

from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils import validate_input_cmd_args


def create_directory_if_not_exists(directory: Path) -> None:
    """
    Create a directory.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        error(f"Failed to create directory {directory}: {e}")
        exit(1)


def find_running_service_names(
    instance_type: InstanceType,
    only_system_folders: bool = False,
    only_user_folders: bool = False,
    k8s_config: KubernetesConfig | None = None,
) -> list[str]:
    """
    List running Vantage6 servers.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to find running services for
    only_system_folders : bool, optional
        Whether to look for system-based services or not. By default False.
    only_user_folders : bool, optional
        Whether to look for user-based services or not. By default False.
    k8s_config : KubernetesConfig, optional
        The Kubernetes configuration to use. If None, the default Kubernetes
        configuration will be used.

    Returns
    -------
    list[str]
        List of release names that are running
    """
    # Input validation
    if k8s_config:
        validate_input_cmd_args(
            k8s_config.context, "k8s_config.context", allow_none=True
        )
        validate_input_cmd_args(
            k8s_config.namespace, "k8s_config.namespace", allow_none=True
        )
    validate_input_cmd_args(instance_type, "instance type", allow_none=False)
    if only_system_folders and only_user_folders:
        error("Cannot use both only_system_folders and only_user_folders")
        exit(1)

    # Create the command
    command = [
        "helm",
        "list",
        "--output",
        "json",  # Get structured output
    ]

    if k8s_config and k8s_config.context:
        command.extend(["--kube-context", k8s_config.context])

    if k8s_config and k8s_config.namespace:
        command.extend(["--namespace", k8s_config.namespace])
    else:
        command.extend(["--all-namespaces"])

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        error(f"Failed to list Helm releases: {e}")
        return []
    except FileNotFoundError:
        error(
            "Helm command not found. Please ensure Helm is installed and available in "
            "the PATH."
        )
        return []

    try:
        releases = json.loads(result.stdout)
    except json.JSONDecodeError:
        error("Failed to parse Helm output as JSON")
        return []

    # filter services for the vantage6 services that are sought. These have
    # the following pattern:
    # f"{APPNAME}-{name}-{scope}-{instance_type.value}"

    # filter for the instance type
    svc_starts_with = f"{APPNAME}-"
    if only_system_folders:
        svc_ends_with = f"system-{instance_type.value}"
    elif only_user_folders:
        svc_ends_with = f"user-{instance_type.value}"
    else:
        svc_ends_with = f"-{instance_type.value}"

    matching_services = []
    for release in releases:
        release_name = release.get("name", "")

        # Check if this is a Vantage6 server release
        is_matching_service = (
            release_name.startswith(svc_starts_with)
            and release_name.endswith(svc_ends_with)
            and instance_type.value in release_name
        )

        if is_matching_service:
            matching_services.append(release_name)

    return matching_services


def select_running_service(
    running_services: list[str],
    instance_type: InstanceType,
) -> str:
    """
    Select a running service from the list of running services.
    """
    try:
        name = q.select(
            f"Select a {instance_type.value}:",
            choices=running_services,
        ).unsafe_ask()
    except KeyboardInterrupt:
        error("Aborted by user!")
        exit(1)
    return name


def get_main_cli_command_name(instance_type: InstanceType) -> str:
    """
    Get the main CLI command name for a given instance type.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the main CLI command name for
    """
    if instance_type == InstanceType.SERVER:
        return CLICommandName.SERVER.value
    elif instance_type == InstanceType.ALGORITHM_STORE:
        return CLICommandName.ALGORITHM_STORE.value
    elif instance_type == InstanceType.NODE:
        return CLICommandName.NODE.value
    elif instance_type == InstanceType.AUTH:
        return CLICommandName.AUTH.value
    else:
        raise ValueError(f"Invalid instance type: {instance_type}")


def check_running(
    helm_release_name: str, instance_type: InstanceType, name: str, system_folders: bool
) -> bool:
    """
    Check if the instance is already running.

    Parameters
    ----------
    helm_release_name : str
        The name of the Helm release.
    instance_type : InstanceType
        The type of instance to check
    name : str
        The name of the instance to check
    system_folders : bool
        Whether to use system folders or not

    Returns
    -------
    bool
        True if the instance is already running, False otherwise
    """
    running_services = find_running_service_names(
        instance_type=instance_type,
        only_system_folders=system_folders,
        only_user_folders=not system_folders,
    )
    return helm_release_name in running_services


def get_config_name_from_helm_release_name(
    helm_release_name: str, is_store: bool = False
) -> str:
    """
    Get the config name from a helm release name.

    Parameters
    ----------
    helm_release_name : str
        The name of the Helm release
    is_store : bool, optional
        Whether the instance is a store or not. By default False.

    Returns
    -------
    str
        The config name
    """
    # helm release name is structured as:
    # f"{APPNAME}-{name}-{scope}-{instance_type}"
    # we want to get the name from the service name
    if is_store:
        # for store, the instance type is `algorithm-store` which contains an additional
        # hyphen
        return "-".join(helm_release_name.split("-")[1:-3])
    else:
        return "-".join(helm_release_name.split("-")[1:-2])


def extract_name_and_is_sandbox(name: str | None, is_sandbox: bool) -> tuple[str, bool]:
    """
    Extract the name and is_sandbox from the name.

    Note that the name may be None: this occurs before when this function is called
    before the user has selected a name. This scenario is fine because when the user
    selects a name interactively, the name never ends with the .sandbox suffix.

    Parameters
    ----------
    name : str | None
        The name of the instance
    is_sandbox : bool
        Whether the instance is a sandbox instance

    Returns
    -------
    tuple[str, bool]
        The name and is_sandbox
    """
    if name and name.endswith(SANDBOX_SUFFIX):
        return name[: -len(SANDBOX_SUFFIX)], True
    else:
        return name, is_sandbox


def generate_password(password_length: int = 16) -> str:
    """
    Generate a strong password that meets the password policy requirements.

    This ensures that the password has at least 8 characters, one uppercase letter,
    one lowercase letter, one number and one special character.

    Parameters
    ----------
    password_length : int, optional
        The length of the password to generate. By default 16.

    Returns
    -------
    str
        The generated password
    """
    import secrets
    import string

    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = "".join(secrets.choice(alphabet) for i in range(password_length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in string.punctuation for c in password)
        ):
            break
    return password


def create_kubernetes_secret(
    core_api: k8s_client.CoreV1Api,
    secret_name: str,
    namespace: str,
    secret_data: dict[str, str],
) -> None:
    """
    Create a Kubernetes secret.

    Parameters
    ----------
    core_api: k8s_client.CoreV1Api
        The Kubernetes Core API instance
    secret_name: str
        The name of the secret
    namespace: str
        The namespace where the secret will be created
    secret_data: dict[str, str]
        The data to be stored in the secret
    """
    secret_body = k8s_client.V1Secret(
        metadata=k8s_client.V1ObjectMeta(name=secret_name, namespace=namespace),
        type="Opaque",
        string_data=secret_data,
    )
    core_api.create_namespaced_secret(namespace=namespace, body=secret_body)
