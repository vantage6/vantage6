from typing import Any

import click
import questionary as q

from vantage6.common import info
from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.algostore.new import algo_store_configuration_questionaire
from vantage6.cli.auth.new import auth_configuration_questionaire
from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_API_SERVICE_SYSTEM_FOLDERS
from vantage6.cli.hq.new import hq_configuration_questionaire
from vantage6.cli.hub.utils.enum import AuthCredentials
from vantage6.cli.k8s_config import get_k8s_node_names, select_k8s_config
from vantage6.cli.utils import prompt_config_name


@click.command()
@click.option(
    "-n", "--name", default=None, help="name of the configuration you want to create."
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
    default=DEFAULT_API_SERVICE_SYSTEM_FOLDERS,
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

    This will create production-ready configurations for the vantage6 hub's components,
    i.e. HQ, auth, algorithm store, ui, as well as related services such as RabbitMQ
    and Prometheus.
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
        "keycloak": {
            "redirectUris": [base_config["ui_url"], "http://localhost:7681"],
            "k8sNodeName": base_config["k8sNodeName"],
        },
        "database": {
            "k8sNodeName": base_config["k8sNodeName"],
        },
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

    # create hq service configuration
    info("Now, let's setup the vantage6 HQ...")
    hq_name = name
    extra_config = {
        "hq": {
            "baseUrl": base_config["hq_url"],
            "keycloak": {
                "adminPassword": auth_config["keycloak"]["adminPassword"],
                "adminClientSecret": auth_config["keycloak"]["adminClientSecret"],
                "url": base_config["auth_url"],
            },
            "logging": {
                "level": base_config["log_level"],
            },
        },
        "database": {
            "k8sNodeName": base_config["k8sNodeName"],
        },
        "ui": {
            "keycloak": {
                "publicUrl": base_config["auth_url"],
            },
        },
    }
    new(
        config_producing_func=hq_configuration_questionaire,
        config_producing_func_args=(hq_name, system_folders),
        name=hq_name,
        system_folders=system_folders,
        type_=InstanceType.HQ,
        extra_config=extra_config,
    )

    # create algorithm store service configuration
    if base_config["has_store"]:
        info("Finally, let's setup the algorithm store...")
        store_name = f"{name}-store"
        extra_config = {
            "store": {
                "keycloak": {
                    "adminPassword": auth_config["keycloak"]["adminPassword"],
                    "adminClientSecret": auth_config["keycloak"]["adminClientSecret"],
                    "url": base_config["auth_url"],
                },
                "vantage6HQUri": base_config["hq_url"],
                "logging": {
                    "level": base_config["log_level"],
                },
                "baseUrl": base_config["store_url"],
            },
            "database": {
                "k8sNodeName": base_config["k8sNodeName"],
            },
        }
        if auth_config["keycloak"].get("smtpServer") is not None:
            extra_config["store"]["smtpServer"] = {
                "host": auth_config["keycloak"]["smtpServer"]["host"],
                "port": auth_config["keycloak"]["smtpServer"]["port"],
                "from": auth_config["keycloak"]["smtpServer"]["from"],
            }
            if auth_config["keycloak"]["smtpServer"].get("user") is not None:
                extra_config["store"]["smtpServer"]["user"] = auth_config["keycloak"][
                    "smtpServer"
                ]["user"]
            if auth_config["keycloak"]["smtpServer"].get("password") is not None:
                extra_config["store"]["smtpServer"]["password"] = auth_config[
                    "keycloak"
                ]["smtpServer"]["password"]
            if auth_config["keycloak"]["smtpServer"].get("replyTo") is not None:
                extra_config["store"]["smtpServer"]["replyTo"] = auth_config[
                    "keycloak"
                ]["smtpServer"]["replyTo"]
            if auth_config["keycloak"]["smtpServer"].get("starttls") is not None:
                extra_config["store"]["smtpServer"]["starttls"] = auth_config[
                    "keycloak"
                ]["smtpServer"]["starttls"]
            if auth_config["keycloak"]["smtpServer"].get("ssl") is not None:
                extra_config["store"]["smtpServer"]["ssl"] = auth_config["keycloak"][
                    "smtpServer"
                ]["ssl"]
        new(
            config_producing_func=algo_store_configuration_questionaire,
            config_producing_func_args=(store_name, system_folders),
            name=store_name,
            system_folders=system_folders,
            type_=InstanceType.ALGORITHM_STORE,
            extra_config=extra_config,
        )

    _print_credentials_one_time(auth_credentials, auth_config["keycloak"])


def _get_base_config() -> dict[str, Any]:
    """
    Get the base configuration for a vantage6 hub's components.
    """
    base_config = {}
    k8s_node_names = get_k8s_node_names()
    base_config["k8sNodeName"] = q.select(
        "What is the name of the k8s node you are using?",
        choices=k8s_node_names,
        default=k8s_node_names[0],
    ).unsafe_ask()
    base_config["hq_url"] = q.text(
        "On what address will the HQ be reachable?",
        default="https://hq.vantage6.ai",
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
    base_config["log_level"] = q.select(
        "What is the log level for the algorithm store?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    ).unsafe_ask()
    return base_config


def _print_credentials_one_time(
    credentials: dict[AuthCredentials, Any] | None, keycloak_config: dict
) -> None:
    """
    Print the used credentials one time.

    Parameters
    ----------
    credentials: dict[AuthCredentials, Any] | None
        Dictionary with the credentials for the authentication service.
    keycloak_config: dict
        Keycloak section of the auth configuration
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
    info("You can login to vantage6 with the following credentials:")
    info(f"Username: {keycloak_config.get('adminUser', 'admin')}")
    info(f"Password: {keycloak_config['adminPassword']}")
    info("--------------------------------")
