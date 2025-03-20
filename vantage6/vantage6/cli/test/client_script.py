import click

from importlib.machinery import SourceFileLoader
from pathlib import Path
from requests.exceptions import ConnectionError
from rich.console import Console

from vantage6.cli.dev.create import create_demo_network
from vantage6.cli.dev.remove import remove_demo_network
from vantage6.cli.dev.start import start_demo_network
from vantage6.cli.dev.stop import stop_demo_network
from vantage6.cli.utils import error
from vantage6.client import Client
from vantage6.common.globals import Ports


@click.command()
@click.option(
    "--script", type=str, required=True, help="Path of the script to test the algorithm"
)
@click.option(
    "--algorithm-image", type=str, default=None, help="Algorithm Docker image to use"
)
@click.option(
    "--algorithm-input", type=dict, default=None, help="Algorithm input argument"
)
@click.option(
    "--create-dev-network",
    is_flag=True,
    help="Create a new dev network to run the test",
)
@click.option(
    "--start-dev-network",
    type=bool,
    default=False,
    help="Start a dev network to run the test",
)
@click.option(
    "-n", "--name", default=None, type=str, help="Name for your development setup"
)
@click.option(
    "--server-url",
    type=str,
    default="http://host.docker.internal",
    help="Server URL to point to. If you are using Docker Desktop, "
    "the default http://host.docker.internal should not be changed.",
)
@click.option(
    "-i", "--image", type=str, default=None, help="Server Docker image to use"
)
@click.option(
    "--keep",
    type=bool,
    default=False,
    help="Keep the dev network after finishing the test",
)
@click.option(
    "--add-dataset",
    type=(str, click.Path()),
    default=[],
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file.",
)
@click.option(
    "--database",
    type=str,
    default=None,
    help="Label of the database to be used for the test",
)
@click.pass_context
def cli_test_client_script(
    click_ctx: click.Context,
    script: Path,
    algorithm_image: str,
    algorithm_input: str,
    name: str,
    server_url: str,
    create_dev_network: bool,
    start_dev_network: bool,
    image: str,
    keep: bool,
    add_dataset: list[tuple[str, Path]] = (),
    database: str = None,
) -> None:
    """
    Run a script for testing an algorithm on a dev network.
    The path to the script must be provided as an argument.
    """
    # create the network
    if create_dev_network:
        click_ctx.invoke(
            create_demo_network,
            name=name,
            num_nodes=3,
            server_url=server_url,
            server_port=Ports.DEV_SERVER.value,
            image=image,
            extra_server_config=None,
            extra_node_config=None,
            add_dataset=add_dataset,
        )

    # start the server and nodes
    if create_dev_network or start_dev_network:
        click_ctx.invoke(
            start_demo_network,
            name=name,
            server_image=image,
            node_image=image,
        )

    client = Client("http://localhost", Ports.DEV_SERVER.value, "/api")
    try:
        client.authenticate("dev_admin", "password")
    except ConnectionError:
        error(
            "Could not connect to the server. Please check if a dev network is running."
        )
        return None

    script_module = SourceFileLoader("test_script", script).load_module()
    test_class = script_module.get_test_class(client)

    result = test_class.test(algorithm_image, algorithm_input, database)

    if result["passed"]:
        msg = ":heavy_check_mark: [green]Test passed[/green]"
    else:
        msg = ":x: [red]Test failed[/red]"

    console = Console()
    console.print(msg)

    # clean up the test resources
    if not keep:
        click_ctx.invoke(stop_demo_network, name=name)
        click_ctx.invoke(remove_demo_network, name=name)

    return result
