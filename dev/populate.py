"""
Script to populate the server with basic fixtures.
"""

import argparse
from pathlib import Path

from vantage6.cli.sandbox.populate import populate_server_dev
from vantage6.cli.sandbox.populate.helpers.utils import NodeConfigCreationDetails

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
parser.add_argument(
    "--populate-marker",
    type=str,
    default=".devspace/vantage6_populate_done",
    help="Path to the populate marker file",
)
args = parser.parse_args()

number_of_nodes = args.number_of_nodes
task_directory = args.task_directory
task_namespace = args.task_namespace
node_starting_port_number = args.starting_port_number
populate_marker = args.populate_marker

#
# Required directories
#
dev_dir = Path("dev")
dev_dir.mkdir(exist_ok=True)
dev_data_dir = Path("dev") / ".data"
dev_data_dir.mkdir(exist_ok=True)

# create object with details for node config creation
node_config_creation_details = NodeConfigCreationDetails(
    node_starting_port_number=node_starting_port_number,
    dev_dir=dev_dir,
    task_directory=task_directory,
    task_namespace=task_namespace,
)

#
# Call common script in CLI to populate the server
#
report_populate_server = populate_server_dev(
    server_url="http://localhost:7601/server",
    auth_url="http://localhost:8080",
    number_of_nodes=number_of_nodes,
    node_config_creation_details=node_config_creation_details,
)

# Create marker file
if report_populate_server:
    with open(populate_marker, "w") as f:
        f.write(report_populate_server)
