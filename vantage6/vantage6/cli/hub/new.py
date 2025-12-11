from typing import Any

import click
import questionary as q

from vantage6.common import info
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.auth.new import auth_configuration_questionaire
from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.hub.utils.enum import AuthCredentials
from vantage6.cli.k8s_config import select_k8s_config
from vantage6.cli.server.new import server_configuration_questionaire
from vantage6.cli.utils import prompt_config_name


@click.command()
@click.option(
    "-n", "--name", default=None, help="name of the configuration you want to use."
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Use system folders instead of user folders. This is the default",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Use user folders instead of system folders",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option("--namespace", default=None, help="Kubernetes namespace to use")
def cli_hub_new(
    name: str,
    system_folders: bool,
    context: str | None,
    namespace: str | None,
) -> None:
    """
    Create production-ready configuration for a complete vantage6 hub.

    This will create production-ready configurations for the server, auth, algorithm
    store, ui, as well as related services such as RabbitMQ and Prometheus.
    """
    name = prompt_config_name(name)
    k8s_cfg = select_k8s_config(context=context, namespace=namespace)

    # get basic general configuration (e.g. URLs for the services)
    info("Starting with the basic configuration...")
    base_config = _get_base_config()

    # create authentication service configuration
    info("Now, let's setup the authentication service...")
    extra_config = {
        # add http://localhost:7681 as that is used by the Python client
        "keycloak": {"redirectUris": [base_config["ui_url"], "http://localhost:7681"]}
    }
    auth_name = f"{name}-auth"
    auth_credentials = {}
    auth_config = new(
        config_producing_func=auth_configuration_questionaire,
        config_producing_func_args=(auth_name, k8s_cfg, auth_credentials),
        name=auth_name,
        system_folders=system_folders,
        type_=InstanceType.AUTH,
        extra_config=extra_config,
    )

    # create server service configuration
    info("Now, let's setup the vantage6 server...")
    extra_config = {
        "server": {
            "keycloakAdminClientSecret": auth_config["keycloak"]["adminClientSecret"]
        }
    }
    new(
        config_producing_func=server_configuration_questionaire,
        config_producing_func_args=(name, system_folders),
        name=name,
        system_folders=system_folders,
        type_=InstanceType.SERVER,
        extra_config=extra_config,
    )

    # create algorithm store service configuration
    # TODO
    if base_config["has_store"]:
        info("Finally, let's setup the algorithm store...")
        pass

    _print_credentials_one_time(auth_credentials)


def _get_base_config() -> dict[str, Any]:
    """
    Get the base configuration for a vantage6 hub.
    """
    base_config = {}
    base_config["server_url"] = q.text(
        "On what address will the vantage6server be reachable?",
        default="https://server.vantage6.ai",
    ).unsafe_ask()
    base_config["auth_url"] = q.text(
        "On what address will the auth service be reachable?",
        default="https://auth.vantage6.ai",
    ).unsafe_ask()

    base_config["ui_url"] = q.text(
        "On what address will the UI be reachable?",
        default="https://ui.vantage6.ai",
    ).unsafe_ask()

    base_config["has_store"] = q.confirm(
        "Do you want to use an algorithm store?",
        default=True,
    ).unsafe_ask()
    if base_config["has_store"]:
        base_config["store_url"] = q.text(
            "On what address will the algorithm store be reachable?",
            default="https://store.vantage6.ai",
        ).unsafe_ask()
    return base_config


def _print_credentials_one_time(credentials: dict[AuthCredentials, Any]) -> None:
    """
    Print the used credentials one time.
    """
    if not credentials:
        return
    info("--------------------------------")
    info(
        "In setting up the service, you generated credentials that have been stored"
        " in Kubernetes secrets."
    )
    info(
        "Do NOT delete the Kubernetes secrets as long as you use this authentication "
        "service."
    )
    info("This is a one-time print of the credentials. They will not be printed again.")
    info("--------------------------------")
    for credential, value in credentials.items():
        info(f"{credential.description}: {value}")
    info("--------------------------------")
