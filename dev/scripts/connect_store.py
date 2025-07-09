"""
Development script to connect the server to the local store.
"""

import json

from pathlib import Path

from vantage6.common.enum import AlgorithmStepType
from vantage6.client import Client


def connect_store(client: Client, dev_dir: Path) -> str:
    """
    Connect the server to the local store.

    Arguments
    ---------
    client: Client
        The client to use to connect to the server.
    dev_dir: Path
        The directory to use to store the development data.
    """

    existing_stores = client.store.list().get("data", [])
    existing_urls = [store["url"] for store in existing_stores]
    summary = "=== Store Connection Summary ===\n"

    # URL should be retrieved from the store, see issue:
    # https://github.com/vantage6/vantage6/issues/1824
    local_store_url = "http://localhost:7602/store"
    client.store.url = local_store_url
    client.store.store_id = 1
    if local_store_url not in existing_urls:
        summary += "Registering local store\n"
        client.store.create(
            algorithm_store_url=local_store_url,
            name="Local store",
            all_collaborations=True,
        )

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

    with open(dev_dir / "v6-session-basic-algorithm-store.json", "r") as f:
        algorithm_store = json.load(f)
        function_metadata = algorithm_store["functions"]

    summary += "Creating Session Basics algorithm\n"
    client.algorithm.create(
        name="Session Basics",
        description="A set of basic algorithms for a session management",
        image="harbor2.vantage6.ai/algorithms/session-basics:latest",
        vantage6_version="5.0.0",
        code_url="https://github.com/vantage6-ai/v6-session-basics",
        partitioning="horizontal",
        functions=function_metadata,
    )

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
                "display_name": "Get the network diagnostics performed on all the nodes",
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
