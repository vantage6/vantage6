"""
Development script to connect HQ to the local store.
"""

import time
from http import HTTPStatus

import requests

from vantage6.common import error, info
from vantage6.common.enum import AlgorithmStepType
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
                except Exception:
                    error(f"Store returns unexpected error: {result.status_code}")
                print_unexpected_error = False
        except Exception:
            info(f"Store not ready yet, waiting {wait_time} seconds...")
        time.sleep(wait_time)

    if not ready:
        error("Store did not become ready in time. Exiting...")
        exit(1)
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

    # Remove existing algorithm
    # This is broken, see issue: https://github.com/vantage6/vantage6/issues/1824
    algorithms = client.algorithm.list(name="session basic example")["data"]
    if len(algorithms) > 0:
        summary += f"Removing existing algorithm {algorithms[0]['name']}\n"
        client.algorithm.delete(id_=algorithms[0]["id"])

    # Download the algorithm store from the github repo. This ensures that the data is
    # always up to date.
    try:
        url = (
            "https://raw.githubusercontent.com/vantage6/v6-session-basics/"
            "main/algorithm_store.json"
        )
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        algorithm_json = response.json()
        function_metadata = algorithm_json["functions"]
    except requests.exceptions.RequestException as e:
        # Fallback to local file if download fails
        print(f"Warning: Could not download algorithm store from GitHub: {e}")
        print("Not putting the algorithm in the store.")
        function_metadata = []

    summary += "Creating Session Basics algorithm\n"
    client.algorithm.create(
        name="Session Basics",
        description="A set of basic algorithms for a session management",
        image="harbor2.vantage6.ai/algorithms/session-basics:latest",
        vantage6_version="5.0.0",
        code_url="https://github.com/vantage6-ai/v6-session-basics",
        partitioning="horizontal",
        functions=function_metadata or [],
    )

    # TODO: v5+ get this json data by downloading it from the github repo - that ensures
    # that the data is always up to date.
    summary += "Creating Network Diagnostics algorithm\n"
    client.algorithm.create(
        name="Network Diagnostics",
        description=(
            "Functions to diagnose network policies, that is, to what extent the "
            "jobs running on a V6 Node could have access to the internal k8s network "
            "or to the outside world."
        ),
        image="ghcr.io/hcadavid/v6-sessions-k8s-diagnostics:latest",
        vantage6_version="5.0.0",
        code_url="https://github.com/hcadavid/v6-sessions-k8s-diagnostics",
        partitioning="horizontal",
        functions=[
            {
                "name": "network_status",
                "display_name": "Get the network diagnostics performed on a given node",
                "standalone": True,
                "description": "Get the network diagnostics performed on a given node",
                "ui_visualizations": [],
                "step_type": AlgorithmStepType.FEDERATED_COMPUTE.value,
                "arguments": [
                    {
                        "has_default_value": True,
                        "name": "sleep_time",
                        "display_name": "Delay ",
                        "description": (
                            "Delay in seconds before finishing the the diagnostics "
                            "task (useful to keep the POD running and access it to "
                            "perform further tests) "
                        ),
                        "type": "integer",
                        "default_value": "1",
                        "is_frontend_only": False,
                    }
                ],
                "databases": [],
            },
            {
                "name": "central_network_diagnostics",
                "display_name": (
                    "Get the network diagnostics performed on all the nodes"
                ),
                "standalone": True,
                "description": (
                    "Get the network diagnostics performed on all the nodes within a "
                    "collaboration"
                ),
                "ui_visualizations": [],
                "step_type": AlgorithmStepType.CENTRAL_COMPUTE.value,
                "arguments": [
                    {
                        "has_default_value": True,
                        "name": "sleep_time",
                        "display_name": "Delay ",
                        "description": (
                            "Delay in seconds before finishing the the diagnostics "
                            "task (useful to keep the PODs running on all the nodes "
                            "to access them and perform further inspections) "
                        ),
                        "type": "integer",
                        "default_value": "1",
                        "is_frontend_only": False,
                    }
                ],
                "databases": [],
            },
        ],
    )

    return summary
