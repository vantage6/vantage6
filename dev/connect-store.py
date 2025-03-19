"""
Development script to configure the server

The `devspace` commands use this script to connect the server to the local
store.
"""

from vantage6.client import Client
from pathlib import Path

dev_dir = Path("dev") / ".data"
dev_dir.mkdir(exist_ok=True)

client = Client("http://localhost", 7601, "/server", log_level="error")
client.authenticate("root", "root")

existing_stores = client.store.list().get("data", [])
existing_urls = [store["url"] for store in existing_stores]

# TODO make the path settable
local_store_url = "http://localhost:7602/store"
client.store.url = local_store_url
client.store.store_id = 1
if not local_store_url in existing_urls:
    store_response = client.store.create(
        algorithm_store_url=local_store_url,
        name="Local store",
        all_collaborations=True,
        force=True,  # required to link localhost store
    )
else:
    store_response = client.store.list(name="Local store")["data"][0]

# Remove existing algorithm
# client.store.url = store_response["url"]
# This is broken, see issue: https://github.com/vantage6/vantage6/issues/1824
# client.store.set(id_=store_response["id"])
algorithms = client.algorithm.list(name="session basic example")["data"]
if len(algorithms) > 0:
    print(f"Removing existing algorithm {algorithms[0]['name']}")
    client.algorithm.delete(id_=algorithms[0]["id"])

client.algorithm.create(
    name="session basic example",
    description="A basic example of a session algorithm",
    image="harbor2.vantage6.ai/algorithms/session-basics:latest",
    vantage6_version="5.0.0",
    code_url="https://github.com/vantage6-ai/v6-session-basics",
    partitioning="horizontal",
    functions=[
        {
            "name": "read_csv",
            "display_name": "Read CSV file",
            "standalone": True,
            "description": "",
            "ui_visualizations": [],
            "type": "federated",
            "arguments": [],
            "databases": [{"description": "", "name": "Database"}],
        },
        {
            "name": "pre_process",
            "display_name": "Change column dtype",
            "standalone": True,
            "description": "Change data type of particular column (e.g. string to int)",
            "ui_visualizations": [],
            "type": "federated",
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
            "description": "",
            "ui_visualizations": [],
            "type": "federated",
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
