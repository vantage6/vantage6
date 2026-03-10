from typing import Any
from urllib.parse import urlparse

import click
import questionary as q
import yaml

from vantage6.common import info
from vantage6.common.globals import (
    InstanceType,
    Ports,
)

from vantage6.cli.algostore.new import algo_store_configuration_questionaire
from vantage6.cli.auth.new import (
    auth_configuration_questionaire,
    global_auth_settings_questionaire,
)
from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_API_SERVICE_SYSTEM_FOLDERS
from vantage6.cli.hq.new import hq_configuration_questionaire
from vantage6.cli.hub.utils.enum import AuthCredentials
from vantage6.cli.k8s_config import (
    KubernetesConfig,
    get_k8s_node_names,
    select_k8s_config,
)
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

    global_hub_config = _create_hub_config(name, base_config, k8s_cfg)

    # create authentication service configuration
    info("Now, let's setup the authentication service...")
    auth_name = f"{name}-auth"
    auth_credentials = {}
    extra_config = {
        "keycloak": {
            # Keycloak is exposed via Ingress (TLS terminated at Ingress)
            "behindIngress": {
                "enabled": True,
                "proxyHeaders": "xforwarded",
                "httpPort": 7680,
            },
            "hostname": base_config["auth_url"],
        }
    }
    auth_config = new(
        config_producing_func=auth_configuration_questionaire,
        config_producing_func_args=(auth_name, k8s_cfg, auth_credentials),
        name=auth_name,
        system_folders=system_folders,
        type_=InstanceType.AUTH,
        extra_config=extra_config,
        save_config_file=False,
    )

    # create hq service configuration
    info("Now, let's setup the vantage6 HQ...")
    hq_name = name
    extra_config = {
        "hq": {
            "logging": {
                "level": base_config["log_level"],
            },
        },
    }
    hq_config = new(
        config_producing_func=hq_configuration_questionaire,
        config_producing_func_args=(hq_name, system_folders),
        name=hq_name,
        system_folders=system_folders,
        type_=InstanceType.HQ,
        extra_config=extra_config,
        save_config_file=False,
    )

    # create algorithm store service configuration
    store_config = None
    auth_config_dict = yaml.safe_load(auth_config)
    if base_config["has_store"]:
        info("Finally, let's setup the algorithm store...")
        store_name = f"{name}-store"
        extra_config = {
            "store": {
                "logging": {
                    "level": base_config["log_level"],
                }
            }
        }
        if auth_config_dict.get("keycloak", {}).get("smtpServer") is not None:
            extra_config["store"]["smtpServer"] = {
                "host": auth_config_dict["keycloak"]["smtpServer"]["host"],
                "port": auth_config_dict["keycloak"]["smtpServer"]["port"],
                "from": auth_config_dict["keycloak"]["smtpServer"]["from"],
            }
            if auth_config_dict["keycloak"]["smtpServer"].get("user") is not None:
                extra_config["store"]["smtpServer"]["user"] = auth_config_dict[
                    "keycloak"
                ]["smtpServer"]["user"]
            if auth_config_dict["keycloak"]["smtpServer"].get("password") is not None:
                extra_config["store"]["smtpServer"]["password"] = auth_config_dict[
                    "keycloak"
                ]["smtpServer"]["password"]
            if auth_config_dict["keycloak"]["smtpServer"].get("replyTo") is not None:
                extra_config["store"]["smtpServer"]["replyTo"] = auth_config_dict[
                    "keycloak"
                ]["smtpServer"]["replyTo"]
            if auth_config_dict["keycloak"]["smtpServer"].get("starttls") is not None:
                extra_config["store"]["smtpServer"]["starttls"] = auth_config_dict[
                    "keycloak"
                ]["smtpServer"]["starttls"]
            if auth_config_dict["keycloak"]["smtpServer"].get("ssl") is not None:
                extra_config["store"]["smtpServer"]["ssl"] = auth_config_dict[
                    "keycloak"
                ]["smtpServer"]["ssl"]
        store_config = new(
            config_producing_func=algo_store_configuration_questionaire,
            config_producing_func_args=(store_name, system_folders),
            name=store_name,
            system_folders=system_folders,
            type_=InstanceType.ALGORITHM_STORE,
            extra_config=extra_config,
            save_config_file=False,
        )

    # create the final hub configuration file
    extra_configs_to_render = {
        "auth_config": auth_config,
        "hq_config": hq_config,
    }
    if store_config is not None:
        extra_configs_to_render["store_config"] = store_config
    new(
        config_producing_func=lambda: global_hub_config,
        config_producing_func_args=(),
        name=name,
        system_folders=system_folders,
        type_=InstanceType.HUB,
        save_config_file=True,
        extra_configs_to_render=extra_configs_to_render,
    )

    _print_credentials_one_time(auth_credentials, global_hub_config["keycloak"])


def _get_base_config() -> dict[str, Any]:
    """
    Get the base configuration for a vantage6 hub's components.
    """
    base_config = {}
    info(
        "Logs and prometheus data can currently only be stored on a specific k8s node."
    )
    k8s_node_names = get_k8s_node_names()
    no_local_storage = "Don't store logs and prometheus data"
    k8s_node_name = q.select(
        "In which k8s node do you want to store logs and prometheus data?",
        choices=[no_local_storage] + k8s_node_names,
        default=k8s_node_names[0],
    ).unsafe_ask()
    if k8s_node_name != no_local_storage:
        base_config["k8sNodeName"] = k8s_node_name
    info("We need you to provide a domain where you will deploy the hub services.")
    info("For instance, the domain 'example.com' will lead to the following URLs:")
    info("Authentication:  https://auth.example.com")
    info("HQ:              https://hq.example.com")
    info("UI:              https://portal.example.com")
    info("Algorithm store: https://store.example.com")
    url_domain = q.text(
        "On what domain will the services be reachable?",
        default="vantage6.ai",
    ).unsafe_ask()
    base_config["hq_url"] = f"https://hq.{url_domain}"
    base_config["auth_url"] = f"https://auth.{url_domain}"
    base_config["ui_url"] = f"https://portal.{url_domain}"
    base_config["has_store"] = q.confirm(
        "Do you want to use an algorithm store?",
        default=True,
    ).unsafe_ask()
    if base_config["has_store"]:
        base_config["store_url"] = f"https://store.{url_domain}"
    base_config["log_level"] = q.select(
        "What is the log level for the algorithm store?",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
    ).unsafe_ask()
    return base_config


def _create_hub_config(
    name: str, base_config: dict[str, Any], k8s_cfg: KubernetesConfig
) -> dict[str, Any]:
    """
    Create a hub configuration file (YAML) that aggregates the auth, HQ
    and algorithm store configurations, so the sandbox can be deployed
    via the single hub Helm chart.

    Parameters
    ----------
    name: str
        The name of the hub.
    base_config: dict[str, Any]
        The base configuration for the hub.
    k8s_cfg: KubernetesConfig
        The Kubernetes configuration to use.

    Returns
    -------
    dict[str, Any]
        The hub configuration.
    """

    def _hostname_from_url(url: str) -> str:
        parsed = urlparse(url)
        return parsed.hostname or ""

    urls = {
        "external": {
            "auth": base_config["auth_url"],
            "store": base_config.get("store_url", ""),
            # The UI is typically exposed on portal.<domain>
            "ui": base_config["ui_url"],
            "hq": base_config["hq_url"],
        },
        "internal": {
            "auth": (
                f"http://vantage6-{name}-user-hub-kc-service.{k8s_cfg.namespace}.svc"
                f".cluster.local:{Ports.DEV_AUTH.value}"
            ),
            "store": (
                f"http://vantage6-{name}-user-hub-store.{k8s_cfg.namespace}.svc"
                f".cluster.local:{Ports.DEV_ALGO_STORE.value}"
            ),
            "ui": (
                f"http://vantage6-{name}-user-hub-ui.{k8s_cfg.namespace}.svc"
                f".cluster.local:{Ports.DEV_UI.value}"
            ),
            "hq": (
                f"http://vantage6-{name}-user-hub-hq.{k8s_cfg.namespace}.svc"
                f".cluster.local:{Ports.DEV_HQ.value}"
            ),
        },
    }

    hub_ingress = {
        "enabled": True,
        "hosts": {
            "auth": _hostname_from_url(urls["external"]["auth"]),
            "hq": _hostname_from_url(urls["external"]["hq"]),
            "portal": _hostname_from_url(urls["external"]["ui"]),
            "store": _hostname_from_url(urls["external"]["store"]),
        },
        "tls": {
            "mode": "cert-manager",
            "existingSecrets": {
                "auth": "",
                "hq": "",
                "portal": "",
                "store": "",
            },
        },
        "certManager": {
            "enabled": True,
            "clusterIssuer": "letsencrypt-prod",
        },
    }

    keycloak = {
        "url": urls["external"]["auth"],
    } | global_auth_settings_questionaire()

    global_config = {
        "hubIngress": hub_ingress,
        "urls": urls,
        "keycloak": keycloak,
    }
    if base_config.get("k8sNodeName") is not None:
        global_config["k8sNodeName"] = base_config["k8sNodeName"]
    return global_config


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
