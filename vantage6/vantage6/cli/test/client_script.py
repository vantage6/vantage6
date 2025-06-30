# import click
# import json
# import subprocess
# import sys

# from pathlib import Path

# from rich.console import Console

# from vantage6.cli.dev.create import create_demo_network
# from vantage6.cli.dev.remove import remove_demo_network

# # from vantage6.cli.dev.start import start_demo_network
# # from vantage6.cli.dev.stop import stop_demo_network
# from vantage6.cli.utils import prompt_config_name
# from vantage6.common.globals import Ports

# TEST_FILE_PATH = Path(__file__).parent / "algo_test_scripts" / "algo_test_script.py"


# @click.command()
# @click.option(
#     "--script",
#     type=click.Path(),
#     default=TEST_FILE_PATH,
#     help="Path of the script to test the algorithm. If a script is not provided, the default script is used.",
# )
# @click.option(
#     "--task-arguments",
#     type=str,
#     default=None,
#     help="Arguments to be provided to Task.create function. If --script is provided, this should not be set.",
# )
# @click.option(
#     "--create-dev-network",
#     is_flag=True,
#     help="Create a new dev network to run the test",
# )
# @click.option(
#     "--start-dev-network",
#     is_flag=True,
#     help="Start a dev network to run the test",
# )
# @click.option(
#     "-n", "--name", default=None, type=str, help="Name for your development setup"
# )
# @click.option(
#     "--server-url",
#     type=str,
#     default="http://host.docker.internal",
#     help="Server URL to point to. If you are using Docker Desktop, "
#     "the default http://host.docker.internal should not be changed.",
# )
# @click.option(
#     "-i", "--image", type=str, default=None, help="Server Docker image to use"
# )
# @click.option(
#     "--keep",
#     type=bool,
#     default=False,
#     help="Keep the dev network after finishing the test",
# )
# @click.option(
#     "--add-dataset",
#     type=(str, click.Path()),
#     default=[],
#     multiple=True,
#     help="Add a dataset to the nodes. The first argument is the label of the database, "
#     "the second is the path to the dataset file.",
# )
# @click.pass_context
# def cli_test_client_script(
#     click_ctx: click.Context,
#     script: Path | None,
#     task_arguments: str | None,
#     name: str,
#     server_url: str,
#     create_dev_network: bool,
#     start_dev_network: bool,
#     image: str,
#     keep: bool,
#     add_dataset: list[tuple[str, Path]] = (),
# ) -> int:
#     """
#     Run a script for testing an algorithm on a dev network.
#     The path to the script must be provided as an argument.
#     """
#     if not (script or task_arguments):
#         raise click.UsageError("--script or --task-arguments must be set.")
#     elif script != TEST_FILE_PATH and task_arguments:
#         raise click.UsageError("--script and --task-arguments cannot be set together.")

#     # Check if the task_arguments is a valid JSON string
#     if task_arguments:
#         try:
#             json.loads(task_arguments.replace("'", '"'))
#         except json.JSONDecodeError:
#             raise click.UsageError("task-arguments must be a valid JSON string.")

#     name = prompt_config_name(name)

#     # create the network
#     if create_dev_network:
#         click_ctx.invoke(
#             create_demo_network,
#             name=name,
#             num_nodes=3,
#             server_url=server_url,
#             server_port=Ports.DEV_SERVER.value,
#             image=image,
#             extra_server_config=None,
#             extra_node_config=None,
#             add_dataset=add_dataset,
#         )

#     # start the server and nodes
#     if create_dev_network or start_dev_network:
#         click_ctx.invoke(
#             start_demo_network,
#             name=name,
#             server_image=image,
#             node_image=image,
#         )

#     # run the test script and get the result
#     if not task_arguments:
#         subprocess_args = ["python", script]
#     else:
#         subprocess_args = ["python", script, task_arguments]

#     result = subprocess.run(subprocess_args, stdout=sys.stdout, stderr=sys.stderr)

#     # check the exit code. If the test passed, it should be 0
#     if result.returncode == 0:
#         msg = ":heavy_check_mark: [green]Test passed[/green]"
#     else:
#         msg = ":x: [red]Test failed[/red]"

#     console = Console()
#     console.print(msg)

#     # clean up the test resources. Keep the network if --keep is set, or if the network
#     # was created for this test. If the network was started for this test, stop it but
#     # do not remove it.
#     if not keep:
#         if create_dev_network or start_dev_network:
#             click_ctx.invoke(stop_demo_network, name=name)
#         if create_dev_network:
#             click_ctx.invoke(remove_demo_network, name=name)

#     return result.returncode
