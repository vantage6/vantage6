import base64
import json
import secrets
import string
import subprocess
import sys
from pathlib import Path

import questionary as q
from kubernetes import client as k8s_client
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import error, info
from vantage6.common.globals import (
    APPNAME,
    SANDBOX_SUFFIX,
    InstanceType,
)

from vantage6.cli.globals import CLICommandName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.utils import validate_input_cmd_args
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


def create_directory_if_not_exists(directory: Path) -> None:
    """
    Create a directory.
    """
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        error(f"Failed to create directory {directory}: {e}")
        sys.exit(1)


def find_running_service_names(
    instance_type: InstanceType,
    only_system_folders: bool = False,
    only_user_folders: bool = False,
    k8s_config: KubernetesConfig | None = None,
) -> list[str]:
    """
    List running vantage6 infrastructure components.

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
        sys.exit(1)

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
    is_part_hub = False
    if instance_type in [
        InstanceType.HQ,
        InstanceType.ALGORITHM_STORE,
        InstanceType.AUTH,
    ]:
        is_part_hub = True
        if only_system_folders:
            alternative_svc_ends_with = "system-hub"
        elif only_user_folders:
            alternative_svc_ends_with = "user-hub"
        else:
            alternative_svc_ends_with = "-hub"

    matching_services = []
    for release in releases:
        release_name = release.get("name", "")

        # Check if this is a vantage6 service
        is_matching_service = release_name.startswith(svc_starts_with) and (
            release_name.endswith(svc_ends_with)
            or (is_part_hub and release_name.endswith(alternative_svc_ends_with))
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
        sys.exit(1)
    return name


def get_main_cli_command_name(instance_type: InstanceType) -> str:
    """
    Get the main CLI command name for a given instance type.

    Parameters
    ----------
    instance_type : InstanceType
        The type of instance to get the main CLI command name for
    """
    if instance_type == InstanceType.HQ:
        return CLICommandName.HQ.value
    elif instance_type == InstanceType.ALGORITHM_STORE:
        return CLICommandName.ALGORITHM_STORE.value
    elif instance_type == InstanceType.NODE:
        return CLICommandName.NODE.value
    elif instance_type == InstanceType.AUTH:
        return CLICommandName.AUTH.value
    elif instance_type == InstanceType.HUB:
        return CLICommandName.HUB.value
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
    one lowercase letter, one number and one special character. We are avoiding
    quotes in the password to avoid issues with escaping in YAML.

    Parameters
    ----------
    password_length : int, optional
        The length of the password to generate. By default 16.

    Returns
    -------
    str
        The generated password
    """
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Avoid quotes to prevent YAML escaping issues
    alphabet = "".join(set(alphabet) - {"'", '"'})
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


def update_kubernetes_secret(
    core_api: k8s_client.CoreV1Api,
    secret_name: str,
    namespace: str,
    secret_data: dict[str, str],
) -> None:
    """
    Set keys in a Kubernetes secret, creating the secret if it does not exist.

    Keys that are already in the secret but not in `secret_data` are kept.

    Parameters
    ----------
    core_api: k8s_client.CoreV1Api
        The Kubernetes Core API instance
    secret_name: str
        The name of the secret
    namespace: str
        The namespace of the secret
    secret_data: dict[str, str]
        The keys and values to set
    """
    try:
        create_kubernetes_secret(core_api, secret_name, namespace, secret_data)
    except ApiException as exc:
        # 409 Conflict: the secret already exists, so update it instead
        if exc.status != 409:
            raise
        core_api.patch_namespaced_secret(
            name=secret_name, namespace=namespace, body={"stringData": secret_data}
        )


def kubernetes_secret_exists(
    core_api: k8s_client.CoreV1Api, secret_name: str, namespace: str
) -> bool:
    """
    Check whether a Kubernetes secret exists.

    Parameters
    ----------
    core_api: k8s_client.CoreV1Api
        The Kubernetes Core API instance
    secret_name: str
        The name of the secret
    namespace: str
        The namespace of the secret

    Returns
    -------
    bool
        True if the secret exists, False otherwise
    """
    try:
        core_api.read_namespaced_secret(name=secret_name, namespace=namespace)
    except ApiException as exc:
        if exc.status == 404:
            return False
        raise
    return True


def read_kubernetes_secret_value(
    core_api: k8s_client.CoreV1Api, secret_name: str, namespace: str, key: str
) -> str | None:
    """
    Read a single value from a Kubernetes secret.

    Parameters
    ----------
    core_api: k8s_client.CoreV1Api
        The Kubernetes Core API instance
    secret_name: str
        The name of the secret
    namespace: str
        The namespace of the secret
    key: str
        The key to read

    Returns
    -------
    str | None
        The value, or None if the key is not in the secret
    """
    secret = core_api.read_namespaced_secret(name=secret_name, namespace=namespace)
    value = (secret.data or {}).get(key)
    return base64.b64decode(value).decode() if value is not None else None


def delete_kubernetes_secret(
    core_api: k8s_client.CoreV1Api, secret_name: str, namespace: str
) -> None:
    """
    Delete a Kubernetes secret. Does nothing if the secret does not exist.

    Parameters
    ----------
    core_api: k8s_client.CoreV1Api
        The Kubernetes Core API instance
    secret_name: str
        The name of the secret
    namespace: str
        The namespace of the secret
    """
    try:
        core_api.delete_namespaced_secret(name=secret_name, namespace=namespace)
    except ApiException as exc:
        if exc.status != 404:
            raise


def store_credentials_in_kubernetes_secrets(
    k8s_cfg: KubernetesConfig, credentials: dict[str, dict[str, str]]
) -> None:
    """
    Create Kubernetes secrets with credentials, asking before replacing existing ones.

    If any secret cannot be created, the secrets created so far are deleted again and
    the program exits.

    Parameters
    ----------
    k8s_cfg: KubernetesConfig
        Kubernetes configuration in which the secrets are created
    credentials: dict[str, dict[str, str]]
        The data of each secret, by secret name
    """
    created = []
    try:
        core_api = get_core_api_with_ssl_handling(k8s_cfg.context)
        for secret_name, secret_data in credentials.items():
            if kubernetes_secret_exists(core_api, secret_name, k8s_cfg.namespace):
                replace = q.confirm(
                    f"Kubernetes secret '{secret_name}' already exists in namespace "
                    f"'{k8s_cfg.namespace}'. Replace it?",
                    default=False,
                ).unsafe_ask()
                if not replace:
                    raise RuntimeError(f"Secret '{secret_name}' already exists")
                delete_kubernetes_secret(core_api, secret_name, k8s_cfg.namespace)
            create_kubernetes_secret(
                core_api, secret_name, k8s_cfg.namespace, secret_data
            )
            created.append(secret_name)
    except (RuntimeError, ApiException, HTTPError) as exc:
        error(f"Failed to store credentials in Kubernetes secrets: {exc}")
        for secret_name in created:
            delete_kubernetes_secret(core_api, secret_name, k8s_cfg.namespace)
        sys.exit(1)
    info(
        f"Stored credentials in Kubernetes secrets {', '.join(created)} (namespace "
        f"'{k8s_cfg.namespace}')."
    )


# configuration keys whose value is the name of a Kubernetes secret
SECRET_REFERENCE_KEYS = ("existingSecret", "adminUserSecret")


def referenced_secret_names(config: dict) -> list[str]:
    """
    Get the names of the Kubernetes secrets that a configuration refers to.

    Parameters
    ----------
    config: dict
        The configuration

    Returns
    -------
    list[str]
        Names of the referenced secrets
    """
    names = []
    for key, value in config.items():
        if key in SECRET_REFERENCE_KEYS and isinstance(value, str) and value:
            names.append(value)
        elif isinstance(value, dict):
            names.extend(referenced_secret_names(value))
    return names


def ensure_referenced_secrets_exist(config: dict, k8s_config: KubernetesConfig) -> None:
    """
    Exit if a Kubernetes secret that the configuration refers to does not exist.

    Parameters
    ----------
    config: dict
        The configuration
    k8s_config: KubernetesConfig
        Kubernetes configuration in which the service will be started. A namespace
        in the configuration takes precedence over its namespace.
    """
    names = referenced_secret_names(config)
    if not names:
        return
    namespace = config.get("namespace") or k8s_config.namespace
    try:
        core_api = get_core_api_with_ssl_handling(k8s_config.context)
        missing = [
            name
            for name in names
            if not kubernetes_secret_exists(core_api, name, namespace)
        ]
    except (RuntimeError, ApiException, HTTPError) as exc:
        error(f"Could not check the Kubernetes secrets of the configuration: {exc}")
        sys.exit(1)
    if missing:
        error(
            f"The following Kubernetes secrets are missing in namespace '{namespace}': "
            f"{', '.join(missing)}. They are created by the 'new' command in the "
            "namespace selected there; make sure to use that namespace."
        )
        sys.exit(1)
