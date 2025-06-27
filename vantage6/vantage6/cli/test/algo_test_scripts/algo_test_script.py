import logging
import algo_test_arguments as arguments
import json
import sys

import vantage6.common.task_status as task_status

from vantage6.client import Client
from vantage6.common import error
from vantage6.common.globals import Ports


def create_and_run_task(client: Client, task_args: dict, algo_name: str = "algorithm"):
    """
    Create and run a task using the provided client and task arguments.

    Parameters
    ----------
        client: Client
            The client instance to use for creating and running the task.
        task_args: dict
            The arguments to pass to the task creation method.
        algo_name: str, optional
            The name of the algorithm for logging purposes. Default is "algorithm".

    Raises
    ------
        AssertionError: If the task fails.
    """
    task = client.task.create(**task_args)
    task_id = task["id"]
    client.wait_for_results(task_id)

    try:
        # check if the task has failed
        assert not task_status.has_task_failed(client.task.get(task_id)["status"])

        logging.info(f"Task for {algo_name} completed successfully.")

    except AssertionError:
        error(
            f"Task for {algo_name} failed. Check the log file of the task "
            f"{task_id} for more information."
        )
        exit(1)


def run_test(custom_args: dict | None = None):
    """
    Run a test by creating and running tasks using the provided arguments.

    Parameters
    ----------
    custom_args: dict, optional
        The arguments to pass to the task creation method. If not provided,
        the arguments from the `arguments` module will be used.
    """
    # Create a client and authenticate
    client = Client("http://localhost", Ports.DEV_SERVER.value, "/api")
    try:
        client.authenticate("dev_admin", "password")
    except ConnectionError:
        error(
            "Could not connect to the server. Please check if a dev network is running."
        )
        exit(1)

    # if custom arguments are provided, use them for running the task
    if custom_args:
        create_and_run_task(client, custom_args)

    else:
        # Run the task for each algorithm in the arguments file
        for algo, task_args in arguments.args.items():
            logging.info("Running task for %s", algo)
            logging.info("Task arguments: %s", task_args)
            create_and_run_task(client, task_args, algo)


if __name__ == "__main__":
    # check if arguments are provided
    if len(sys.argv) > 1:
        input_string = sys.argv[1].replace("'", '"')
        json_input = json.loads(input_string)
    else:
        json_input = None

    run_test(json_input)
