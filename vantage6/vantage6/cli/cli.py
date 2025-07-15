import click

from vantage6.cli.server.attach import cli_server_attach
from vantage6.cli.server.files import cli_server_files
from vantage6.cli.server.import_ import cli_server_import
from vantage6.cli.server.list import cli_server_configuration_list
from vantage6.cli.server.new import cli_server_new
from vantage6.cli.server.remove import cli_server_remove
from vantage6.cli.server.shell import cli_server_shell
from vantage6.cli.server.start import cli_server_start
from vantage6.cli.server.stop import cli_server_stop
from vantage6.cli.server.version import cli_server_version
from vantage6.cli.node.attach import cli_node_attach
from vantage6.cli.node.clean import cli_node_clean
from vantage6.cli.node.create_private_key import cli_node_create_private_key
from vantage6.cli.node.files import cli_node_files
from vantage6.cli.node.list import cli_node_list
from vantage6.cli.node.new import cli_node_new_configuration
from vantage6.cli.node.remove import cli_node_remove
from vantage6.cli.node.restart import cli_node_restart
from vantage6.cli.node.set_api_key import cli_node_set_api_key
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.stop import cli_node_stop
from vantage6.cli.node.version import cli_node_version
from vantage6.cli.algorithm.create import cli_algorithm_create
from vantage6.cli.algorithm.update import cli_algorithm_update
from vantage6.cli.algorithm.generate_algorithm_json import (
    cli_algorithm_generate_algorithm_json,
)

# from vantage6.cli.test.client_script import cli_test_client_script
from vantage6.cli.test.feature_tester import cli_test_features

# from vantage6.cli.test.integration_test import cli_test_integration
from vantage6.cli.algostore.attach import cli_algo_store_attach
from vantage6.cli.algostore.new import cli_algo_store_new
from vantage6.cli.algostore.start import cli_algo_store_start
from vantage6.cli.algostore.stop import cli_algo_store_stop
from vantage6.cli.algostore.files import cli_algo_store_files
from vantage6.cli.algostore.list import cli_algo_store_configuration_list
from vantage6.cli.algostore.remove import cli_algo_store_remove
from vantage6.cli.use.context import cli_use_context
from vantage6.cli.use.namespace import cli_use_namespace


# Define the server group
@click.group(name="server")
def cli_server() -> None:
    """
    Manage your vantage6 server instances.
    """


# Define the commands for the server group
cli_server.add_command(cli_server_attach, name="attach")
cli_server.add_command(cli_server_files, name="files")
cli_server.add_command(cli_server_import, name="import")
cli_server.add_command(cli_server_configuration_list, name="list")
cli_server.add_command(cli_server_new, name="new")
cli_server.add_command(cli_server_remove, name="remove")
cli_server.add_command(cli_server_shell, name="shell")
cli_server.add_command(cli_server_start, name="start")
cli_server.add_command(cli_server_stop, name="stop")
cli_server.add_command(cli_server_version, name="version")


# Define the node group
@click.group(name="node")
def cli_node() -> None:
    """
    Manage your vantage6 node instances.
    """


# Define the commands for the node group
cli_node.add_command(cli_node_attach, name="attach")
cli_node.add_command(cli_node_clean, name="clean")
cli_node.add_command(cli_node_create_private_key, name="create-private-key")
cli_node.add_command(cli_node_files, name="files")
cli_node.add_command(cli_node_list, name="list")
cli_node.add_command(cli_node_new_configuration, name="new")
cli_node.add_command(cli_node_remove, name="remove")
cli_node.add_command(cli_node_restart, name="restart")
cli_node.add_command(cli_node_set_api_key, name="set-api-key")
cli_node.add_command(cli_node_start, name="start")
cli_node.add_command(cli_node_stop, name="stop")
cli_node.add_command(cli_node_version, name="version")


# Define the dev group
@click.group(name="dev")
def cli_dev() -> None:
    """
    Quickly manage a test network with a server and several nodes.

    These commands are helpful for local testing of your vantage6 environment.
    """


# TODO add commands for the dev group


# Define the algorithm group
@click.group(name="algorithm")
def cli_algorithm() -> None:
    """
    Manage your vantage6 algorithms.
    """


# Define the commands for the algorithm group
cli_algorithm.add_command(cli_algorithm_create, name="create")
cli_algorithm.add_command(cli_algorithm_update, name="update")
cli_algorithm.add_command(
    cli_algorithm_generate_algorithm_json, name="generate-algorithm-json"
)


# Define the test group
@click.group(name="test")
def cli_test() -> None:
    """
    Execute tests on your vantage6 infrastructure.
    """


# Define the commands for the test group
cli_test.add_command(cli_test_features, name="feature-test")
# cli_test.add_command(cli_test_integration, name="integration-test")
# cli_test.add_command(cli_test_client_script, name="client-script")


# Define the algorithm-store group
@click.group(name="algorithm-store")
def cli_algo_store() -> None:
    """
    Manage your vantage6 algorithm store server instances.
    """


# Define the commands for the test group
cli_algo_store.add_command(cli_algo_store_attach, name="attach")
cli_algo_store.add_command(cli_algo_store_new, name="new")
cli_algo_store.add_command(cli_algo_store_start, name="start")
cli_algo_store.add_command(cli_algo_store_stop, name="stop")
cli_algo_store.add_command(cli_algo_store_files, name="files")
cli_algo_store.add_command(cli_algo_store_configuration_list, name="list")
cli_algo_store.add_command(cli_algo_store_remove, name="remove")


# Add the use group
@click.group(name="use")
def cli_use() -> None:
    """
    Manage Kubernetes context and namespace.
    """


# Define the commands for the use group
cli_use.add_command(cli_use_context, name="context")
cli_use.add_command(cli_use_namespace, name="namespace")


# Define the overall group
@click.group(name="cli", context_settings={"show_default": True})
def cli_complete() -> None:
    """
    The `v6` command line interface allows you to manage your vantage6
    infrastructure.

    It provides a number of subcommands to help you with this task.
    """


# Add the subcommands to the overall group
cli_complete.add_command(cli_node)
cli_complete.add_command(cli_server)
cli_complete.add_command(cli_dev)
cli_complete.add_command(cli_algorithm)
cli_complete.add_command(cli_test)
cli_complete.add_command(cli_algo_store)
cli_complete.add_command(cli_use)
