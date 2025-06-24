"""
Script to populate the server with basic fixtures.
"""

import argparse
import time
from pathlib import Path

from vantage6.client import Client

from scripts.delete_fixtures import delete_fixtures
from scripts.load_fixtures import create_fixtures
from scripts.connect_store import connect_store

#
# Arguments
#
parser = argparse.ArgumentParser(
    description="Load basic fixtures for a given number of nodes"
)
parser.add_argument(
    "--task-directory", type=str, help="Directory to store tasks on the host"
)
parser.add_argument(
    "--number-of-nodes", type=int, default=3, help="Number of nodes to create"
)
parser.add_argument(
    "--task-namespace", type=str, default="vantage6-tasks", help="Task namespace"
)
parser.add_argument(
    "--starting-port-number",
    type=int,
    default=7654,
    help=(
        "The port number to be allocated to the proxy server of the first node. "
        "Additional nodes will use consecutive ports incremented by 1 from this value."
    ),
)
args = parser.parse_args()

number_of_nodes = args.number_of_nodes
task_directory = args.task_directory
task_namespace = args.task_namespace
node_starting_port_number = args.starting_port_number

#
# Required directories
#
dev_dir = Path("dev")
dev_dir.mkdir(exist_ok=True)
dev_data_dir = Path("dev") / ".data"
dev_data_dir.mkdir(exist_ok=True)

#
# Connect to server
#
# Even though the deployment of the server is ready, the server might not be fully
# initialized yet. The first step it to wait till we can authenticate with the keycloak
# service, then we check if the server is fully initialized by checking if the admin
# user is present.
client = Client("http://localhost", 7601, "/server", log_level="error")
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

print("Waiting for the admin user to be present...")
attempt = 1
while attempt <= max_attempts:
    try:

        users = client.user.list(fields=("name"))
        if len(users) > 0:
            print("Admin user found!")
            break
    except Exception as e:
        if attempt == max_attempts:
            print(f"Failed to check if server is online after {max_attempts} attempts.")
            raise e

        time.sleep(5)
        attempt += 1

#
# Create new fixtures
#
# This script can be run multiple times, so we delete the existing fixtures first. We
# also want the development environment to start in case something fails.
#
try:
    delete_fixtures(client)
    create_fixtures(
        client,
        number_of_nodes,
        task_directory,
        task_namespace,
        node_starting_port_number,
        dev_data_dir,
    )
    connect_store(client, dev_dir)
except Exception as e:
    print("=" * 80)
    print("Failed to populate server")
    print(f"Error: {str(e)}")
    print("=" * 80)
