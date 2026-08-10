"""
Development script to connect HQ to the local store.
"""

import sys
import time
from http import HTTPStatus

import requests

from vantage6.common import error, info
from vantage6.common.globals import Ports

from vantage6.client import Client


def _wait_for_store_to_be_online(
    local_store_url: str, local_store_api_path: str
) -> None:
    """
    Wait for the store to be online.

    Parameters
    ---------
    client: Client
        The client to use to connect to vantage6 hub.
    local_store_url: str
        The URL of the local store.
    local_store_api_path: str
        The API path of the local store.
    """
    info(
        f"Waiting for store to be online at {local_store_url}{local_store_api_path}..."
    )
    max_retries = 100
    wait_time = 3
    ready = False
    print_unexpected_error = True
    for _ in range(max_retries):
        try:
            result = requests.get(f"{local_store_url}{local_store_api_path}/version")
            if result.status_code == HTTPStatus.OK:
                ready = True
                break
            elif print_unexpected_error:
                try:
                    error(f"Store returns unexpected error: {result.json()['msg']}")
                except (requests.exceptions.JSONDecodeError, KeyError):
                    error(f"Store returns unexpected error: {result.status_code}")
                print_unexpected_error = False
        except requests.RequestException:
            info(f"Store not ready yet, waiting {wait_time} seconds...")
        time.sleep(wait_time)

    if not ready:
        error("Store did not become ready in time. Exiting...")
        sys.exit(1)
    else:
        info("Store is online!")


def connect_store(client: Client, store_port: int = Ports.DEV_ALGO_STORE.value) -> str:
    """
    Connect HQ to the local store.

    Parameters
    ---------
    client: Client
        The client to use to connect to vantage6 hub.
    store_port: int
        The port of the store to connect to.

    Returns
    -------
    str
        A summary of the store connection process.
    """

    existing_stores = client.store.list().get("data", [])
    summary = "=== Store Connection Summary ===\n"

    # URL should be retrieved from the store, see issue:
    # https://github.com/vantage6/vantage6/issues/1824
    local_store_url = f"http://localhost:{store_port}"
    local_store_api_path = "/store"
    client.store.store_id = 1

    _wait_for_store_to_be_online(local_store_url, local_store_api_path)

    # note that the store is already coupled to HQ in the sandbox/devspace
    # config.
    try:
        store = next(s for s in existing_stores if s["url"] == local_store_url)
        client.store.set(store["id"])
        info(f"Using store with id '{store['id']}'")
    except StopIteration:
        error(
            "Local algorithm store not found. Please register its resources manually."
        )
        return ""

    # register also the other users in the local store
    users_in_store = client.store.user.list()["data"]
    all_users = client.user.list()["data"]
    for user in all_users:
        if user["keycloak_id"] not in [u["keycloak_id"] for u in users_in_store]:
            summary += f"Registering user {user['username']} in local store\n"
            client.store.user.register(username=user["username"], roles=[1])

    return summary
