"""
Script to populate the server with basic fixtures.
"""

import time
import traceback
from pathlib import Path

from vantage6.client import Client
from vantage6.client.utils import LogLevel

from vantage6.cli.sandbox.populate.helpers.connect_store import connect_store
from vantage6.cli.sandbox.populate.helpers.delete_fixtures import delete_fixtures
from vantage6.cli.sandbox.populate.helpers.load_fixtures import create_fixtures


def populate_server(
    server_url: str,
    auth_url: str,
    number_of_nodes: int,
    task_directory: str,
    task_namespace: str,
    node_starting_port_number: int,
    dev_data_dir: Path,
    dev_dir: Path,
    clear_dev_folders: bool = False,
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
    task_directory : str
        The directory containing the task files.
    task_namespace : str
        The namespace of the task.
    node_starting_port_number : int
        The starting port number for the nodes.
    dev_data_dir : Path
        The directory to store the development data.
    dev_dir : Path
        The directory to store the development files.
    clear_dev_folders : bool
        Whether to clear everything inthe dev directory before creating the new
        resources.

    Returns
    -------
    str | None
        A report of the creation process, or None if an error occurred.

    Raises
    ------
    Exception
        If an error occurs while populating the server.
    """
    client = _initalize_client(server_url, auth_url)

    # Create new resources in the server
    # Delete existing resources in the server first, before creating new ones.
    try:
        report_deletion = delete_fixtures(client)
        report_creation = create_fixtures(
            client,
            number_of_nodes,
            task_directory,
            task_namespace,
            node_starting_port_number,
            dev_data_dir,
            clear_dev_folders=clear_dev_folders,
        )
        report_store = connect_store(client, dev_dir)

        return report_deletion + "\n" + report_creation + "\n" + report_store

    except Exception:
        print("=" * 80)
        print("Failed to populate server")
        print(traceback.format_exc())
        print("=" * 80)


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

    print("Waiting for authentication...")
    max_attempts = 120
    attempt = 1

    while attempt <= max_attempts:
        try:
            print(".", end="", flush=True)
            client.authenticate()
            print("Successfully authenticated with server!")
            break
        except Exception as e:
            if attempt == max_attempts:
                print(
                    f"Failed to authenticate after {max_attempts} attempts. "
                    "Server may not be online."
                )
                raise e

            time.sleep(5)
            attempt += 1

    return client
