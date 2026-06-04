import json
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console

from vantage6.cli.sandbox.new import cli_new_sandbox
from vantage6.cli.sandbox.remove import cli_sandbox_remove
from vantage6.cli.sandbox.start import cli_sandbox_start
from vantage6.cli.sandbox.stop import cli_sandbox_stop
from vantage6.cli.utils import prompt_config_name

TEST_FILE_PATH = Path(__file__).parent / "algo_test_scripts" / "algo_test_script.py"


@click.command()
@click.option(
    "--script",
    type=click.Path(),
    # default=TEST_FILE_PATH,
    help="Path of the script to test the algorithm.",
)
@click.option(
    "--task-arguments",
    type=str,
    default=None,
    help="Arguments to be provided to Task.create function. If --script is provided, this should not be set.",
)
@click.option(
    "--create-sandbox",
    is_flag=True,
    help="Create a new sandbox to run the test",
)
@click.option(
    "--start-sandbox",
    is_flag=True,
    help="Start a sandbox to run the test",
)
@click.option("-n", "--name", default=None, type=str, help="Name for your sandbox")
@click.option("--hq-image", type=str, default=None, help="HQ Docker image to use")
@click.option(
    "--store-image", type=str, default=None, help="Algorithm store Docker image to use"
)
@click.option("--node-image", type=str, default=None, help="Node Docker image to use")
@click.option(
    "--extra-hq-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional HQ configuration. This will be appended to the HQ "
    "configuration file",
)
@click.option(
    "--extra-store-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional algorithm store configuration. This will be "
    "appended to the algorithm store configuration file",
)
@click.option(
    "--extra-auth-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional auth configuration. This will be appended to the "
    "auth configuration file",
)
@click.option(
    "--extra-node-config",
    type=click.Path(exists=True),
    default=None,
    help="YAML File with additional node configuration. This will be appended to the "
    "node configuration file",
)
@click.option(
    "--keep",
    type=bool,
    flag_value=True,
    default=False,
    help="Keep the sandbox after finishing the test",
)
@click.option(
    "--add-dataset",
    type=(str, click.Path()),
    default=[],
    multiple=True,
    help="Add a dataset to the nodes. The first argument is the label of the database, "
    "the second is the path to the dataset file.",
)
@click.pass_context
def cli_test_client_script(
    click_ctx: click.Context,
    script: Path | None,
    task_arguments: str | None,
    name: str,
    create_sandbox: bool,
    start_sandbox: bool,
    hq_image: str,
    store_image: str,
    node_image: str,
    extra_hq_config: Path,
    extra_store_config: Path,
    extra_auth_config: Path,
    extra_node_config: Path,
    keep: bool,
    add_dataset: list[tuple[str, Path]] = (),
) -> int:
    """
    Run a script for testing an algorithm on a sandbox network.
    The path to the script must be provided as an argument.
    """
    if not (script or task_arguments):
        raise click.UsageError("--script or --task-arguments must be set.")
    elif script and task_arguments:
        raise click.UsageError("--script and --task-arguments cannot be set together.")

    # Check if the task_arguments is a valid JSON string
    if task_arguments:
        try:
            json.loads(task_arguments.replace("'", '"'))
        except json.JSONDecodeError:
            raise click.UsageError("task-arguments must be a valid JSON string.")

    name = prompt_config_name(name)

    # create the network
    if create_sandbox:
        click_ctx.invoke(
            cli_new_sandbox,
            name=name,
            num_nodes=3,
            hq_image=hq_image,
            store_image=store_image,
            node_image=node_image,
            extra_hq_config=extra_hq_config,
            extra_store_config=extra_store_config,
            extra_auth_config=extra_auth_config,
            extra_node_config=extra_node_config,
            add_dataset=add_dataset,
        )

    # start the server and nodes
    if start_sandbox and not create_sandbox:
        click_ctx.invoke(
            cli_sandbox_start,
            name=name,
            node_image=node_image,
            extra_node_config=extra_node_config,
            add_dataset=add_dataset,
        )

    # run the test script and get the result
    if not task_arguments:
        subprocess_args = ["python", script]
    else:
        subprocess_args = ["python", script, task_arguments]

    result = subprocess.run(subprocess_args, stdout=sys.stdout, stderr=sys.stderr)

    # check the exit code. If the test passed, it should be 0
    if result.returncode == 0:
        msg = ":heavy_check_mark: [green]Test passed[/green]"
    else:
        msg = ":x: [red]Test failed[/red]"

    console = Console()
    console.print(msg)

    # clean up the test resources. Keep the network if --keep is set, or if the network
    # was created for this test. If the network was started for this test, stop it but
    # do not remove it.
    if not keep:
        if start_sandbox or create_sandbox:
            click_ctx.invoke(cli_sandbox_stop, name=name)
        if create_sandbox:
            click_ctx.invoke(cli_sandbox_remove, name=name)

    return result.returncode
