"""
Script to populate the server with basic fixtures.
"""

import time
import traceback
from logging import info

from vantage6.common import error

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.sandbox.populate.helpers.connect_store import connect_store
from vantage6.cli.sandbox.populate.helpers.delete_fixtures import delete_fixtures
from vantage6.cli.sandbox.populate.helpers.load_fixtures import create_fixtures
from vantage6.cli.sandbox.populate.helpers.utils import NodeConfigCreationDetails


def populate_server_dev(
    server_url: str,
    auth_url: str,
    number_of_nodes: int,
    node_config_creation_details: NodeConfigCreationDetails,
) -> str | None:
    """
    Populate the server with basic fixtures.

    Parameters
    ----------
    server_url : str
        The URL of the server to connect to.
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
        If connection/authentication to the server fails.
    """
    client = _initalize_client(server_url, auth_url)

    # Create new resources in the server
    # Delete existing resources in the server first, before creating new ones.
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
        error("Failed to populate server")
        error(traceback.format_exc())
        error("=" * 80)


def populate_server_sandbox(
    server_url: str,
    auth_url: str,
    number_of_nodes: int,
) -> dict:
    """
    Populate sandbox server with basic resources.

    Parameters
    ----------
    server_url : str
        The URL of the server to connect to.
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
        If connection/authentication to the server fails.
    """
    client = _initalize_client(server_url, auth_url)

    try:
        delete_fixtures(client)
        report_creation = create_fixtures(
            client,
            number_of_nodes,
            clear_dev_folders=False,
            return_as_dict=True,
        )
        connect_store(client)
    except Exception:
        error("=" * 80)
        error("Failed to populate server")
        error(traceback.format_exc())
        error("=" * 80)
        exit(1)

    # return the details of the created nodes so that config files can be created
    return report_creation["nodes"]["created"]


def _initalize_client(server_url, auth_url) -> Client:
    """
    Initialize an authenticated client to the server.

    The server may not be ready yet, so we retry until it is.

    Parameters
    ----------
    server_url : str
        The URL of the server to connect to.
    auth_url : str
        The URL of the auth service to connect to.

    Returns
    -------
    Client
        An authenticated client to the server.
    """
    client = Client(
        server_url=server_url,
        auth_url=auth_url,
        log_level=LogLevel.ERROR,
    )

    info("Waiting for authentication...")
    max_attempts = 120
    attempt = 1

    while attempt <= max_attempts:
        try:
            print(".", end="", flush=True)
            client.authenticate()
            info("Successfully authenticated with server!")
            break
        except Exception as e:
            if attempt == max_attempts:
                error(
                    f"Failed to authenticate after {max_attempts} attempts. "
                    "Server may not be online."
                )
                raise e

            time.sleep(5)
            attempt += 1

    return client
