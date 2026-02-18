"""
Script to populate the hub with basic fixtures.
"""

import time
import traceback
from logging import info

import requests

from vantage6.common import error
from vantage6.common.globals import Ports

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.sandbox.populate.helpers.connect_store import connect_store
from vantage6.cli.sandbox.populate.helpers.delete_fixtures import delete_fixtures
from vantage6.cli.sandbox.populate.helpers.load_fixtures import create_fixtures
from vantage6.cli.sandbox.populate.helpers.utils import NodeConfigCreationDetails


def populate_hub_dev(
    hq_url: str,
    auth_url: str,
    number_of_nodes: int,
    node_config_creation_details: NodeConfigCreationDetails,
) -> str | None:
    """
    Populate the hub with basic fixtures.

    Parameters
    ----------
    hq_url : str
        The URL of the HQ to connect to.
    auth_url : str
        The URL of the auth service to connect to.
    number_of_nodes : int
        The number of nodes to create.
    node_config_creation_details : NodeConfigCreationDetails | None
        The details of the node config creation. If None, the node configs will not be
        created.
    clear_dev_folders : bool
        Whether to clear everything inthe dev directory before creating the new
        resources.
    create_node_configs: bool
        Whether to create the node configs. Default is True.

    Returns
    -------
    str | None
        A report of the creation process, or None if an error occurred.

    Raises
    ------
    Exception
        If connection/authentication to the HQ fails.
    """
    client = _initalize_client(hq_url, auth_url)

    # Create new resources in the HQ and store
    # Delete existing resources in the HQ first, before creating new ones.
    try:
        report_deletion = delete_fixtures(client)
        report_creation = create_fixtures(
            client,
            number_of_nodes,
            node_config_creation_details=node_config_creation_details,
            clear_dev_folders=True,
        )
        report_store = connect_store(client)

        return report_deletion + "\n" + report_creation + "\n" + report_store

    except Exception:
        error("=" * 80)
        error("Failed to populate hub")
        error(traceback.format_exc())
        error("=" * 80)


def populate_hub_sandbox(
    hq_url: str,
    auth_url: str,
    number_of_nodes: int,
) -> dict:
    """
    Populate sandbox hub with basic resources.

    Parameters
    ----------
    hq_url : str
        The URL of the HQ to connect to.
    auth_url : str
        The URL of the auth service to connect to.
    number_of_nodes : int
        The number of nodes to create.

    Returns
    -------
    dict
        A dictionary containing the report of the creation process.

    Raises
    ------
    Exception
        If connection/authentication to the HQ fails.
    """
    client = _initalize_client(hq_url, auth_url)

    try:
        delete_fixtures(client)
        report_creation = create_fixtures(
            client,
            number_of_nodes,
            clear_dev_folders=False,
            return_as_dict=True,
        )
        connect_store(client, store_port=Ports.SANDBOX_ALGO_STORE.value)
    except Exception:
        error("=" * 80)
        error("Failed to populate hub")
        error(traceback.format_exc())
        error("=" * 80)
        exit(1)

    # return the details of the created nodes so that config files can be created
    return report_creation["nodes"]["created"]


def _wait_for_keycloak_realm(
    auth_url: str, realm_name: str = "vantage6", timeout: int = 120
) -> None:
    """
    Wait for Keycloak realm to be available before attempting authentication.

    This prevents race conditions where authentication is attempted before
    the realm import job has completed.

    Parameters
    ----------
    auth_url : str
        The URL of the Keycloak auth service.
    realm_name : str
        The name of the realm to wait for. Default is "vantage6".
    timeout : int
        Maximum time to wait in seconds. Default is 120.
    """
    info("Waiting for Keycloak realm to be ready...")
    well_known_url = f"{auth_url}/realms/{realm_name}/.well-known/openid-configuration"
    start_time = time.time()
    attempt = 0

    while time.time() - start_time < timeout:
        attempt += 1
        try:
            resp = requests.get(well_known_url, timeout=5)
            if resp.status_code == 200:
                info("Keycloak realm is ready.")
                return
            elif resp.status_code == 404:
                # Realm doesn't exist yet - wait and retry
                if attempt % 5 == 0:  # Log every 5th attempt
                    info(f"Realm not ready yet (attempt {attempt})...")
                time.sleep(2)
            else:
                # Other HTTP errors - log and retry
                if attempt % 10 == 0:  # Log every 10th attempt
                    info(f"Keycloak returned status {resp.status_code}, retrying...")
                time.sleep(2)
        except requests.exceptions.RequestException:
            # Network errors - wait and retry
            if attempt % 5 == 0:
                info(f"Keycloak not reachable yet (attempt {attempt})...")
            time.sleep(2)

    error(
        f"Timeout: Keycloak realm '{realm_name}' did not become available "
        f"within {timeout} seconds. The realm import job may have failed."
    )
    raise TimeoutError(
        f"Keycloak realm '{realm_name}' not ready after {timeout} seconds"
    )


def _initalize_client(hq_url: str, auth_url: str) -> Client:
    """
    Initialize an authenticated client to the HQ.

    The HQ may not be ready yet, so we retry until it is.

    Parameters
    ----------
    hq_url : str
        The URL of the HQ to connect to.
    auth_url : str
        The URL of the auth service to connect to.

    Returns
    -------
    Client
        An authenticated client to the vantage6 hub.
    """
    # Wait for Keycloak realm to be ready before attempting authentication
    _wait_for_keycloak_realm(auth_url)

    client = Client(
        hq_url=hq_url,
        auth_url=auth_url,
        log_level=LogLevel.WARN,
    )

    info("Waiting for authentication...")
    max_attempts = 120
    attempt = 1

    while attempt <= max_attempts:
        try:
            print(".", end="", flush=True)
            client.authenticate()
            info("Successfully authenticated!")
            break
        except Exception as e:
            if attempt == max_attempts:
                error(
                    f"Failed to authenticate after {max_attempts} attempts. "
                    "Vantage6 hub may not be online."
                )
                raise e

            time.sleep(5)
            attempt += 1

    return client
