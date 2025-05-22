"""
Development script to configure the server

The `devspace` commands use this script to connect the server to the local
store.
"""

from vantage6.client import Client
from pathlib import Path
from vantage6.common.enum import AlgorithmStepType

dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)
client = Client("http://localhost", 7601, "/server", log_level="error")
client.authenticate("admin", "admin")
existing_stores = client.store.list().get("data", [])
existing_urls = [store["url"] for store in existing_stores]

# URL should be retrieved from the store, see issue:
# https://github.com/vantage6/vantage6/issues/1824
local_store_url = "http://localhost:7602/store"
client.store.url = local_store_url
client.store.store_id = 1
if local_store_url not in existing_urls:
    print("Registering local store")
    store_response = client.store.create(
        algorithm_store_url=local_store_url,
        name="Local store",
        all_collaborations=True,
    )
else:
    store_response = client.store.list(name="Local store")["data"][0]

# register also the other users in the local store
users_in_store = client.store.user.list()["data"]
all_users = client.user.list()["data"]
for user in all_users:
    if user["keycloak_id"] not in [u["keycloak_id"] for u in users_in_store]:
        print(f"Registering user {user['username']} in local store")
        client.store.user.register(username=user["username"], roles=[1])

# Remove existing algorithm
# This is broken, see issue: https://github.com/vantage6/vantage6/issues/1824
# client.store.url = store_response["url"]
# client.store.set(id_=store_response["id"])
algorithms = client.algorithm.list(name="session basic example")["data"]
if len(algorithms) > 0:
    print(f"Removing existing algorithm {algorithms[0]['name']}")
    client.algorithm.delete(id_=algorithms[0]["id"])

client.algorithm.create(
    name="Session Basics",
    description="A set of basic algorithms for a session management",
    image="harbor2.vantage6.ai/algorithms/session-basics:latest",
    vantage6_version="5.0.0",
    code_url="https://github.com/vantage6-ai/v6-session-basics",
    partitioning="horizontal",
    functions=[
        {
            "name": "read_csv",
            "display_name": "Read CSV file",
            "standalone": True,
            "description": "Read a CSV file to the local session storage",
            "ui_visualizations": [],
            "step_type": AlgorithmStepType.DATA_EXTRACTION.value,
            "arguments": [],
            "databases": [{"description": "", "name": "Database"}],
        },
        {
            "name": "pre_process",
            "display_name": "Change column dtype",
            "standalone": True,
            "description": "Change data type of particular column (e.g. string to int)",
            "ui_visualizations": [],
            "step_type": AlgorithmStepType.PREPROCESSING.value,
            "arguments": [
                {
                    "has_default_value": False,
                    "name": "column",
                    "display_name": "Column ",
                    "description": "Column to change data type of ",
                    "type": "column",
                    "default_value": "",
                    "is_frontend_only": False,
                },
                {
                    "has_default_value": False,
                    "name": "dtype",
                    "display_name": "New data type",
                    "description": "",
                    "type": "string",
                    "default_value": "",
                    "is_frontend_only": False,
                },
            ],
            "databases": [],
        },
        {
            "name": "sum",
            "display_name": "Sum",
            "standalone": True,
            "description": "Sum the values of a column",
            "ui_visualizations": [],
            "step_type": AlgorithmStepType.FEDERATED_COMPUTE.value,
            "arguments": [
                {
                    "has_default_value": False,
                    "name": "column",
                    "display_name": "Column to sum",
                    "description": "",
                    "type": "column",
                    "default_value": "",
                    "is_frontend_only": False,
                }
            ],
            "databases": [],
        },
    ],
)
