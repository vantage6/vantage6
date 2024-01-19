import os
from pathlib import Path

import click
import questionary as q
from copier import run_update

from vantage6.cli.utils import info


@click.command()
@click.option(
    "-d",
    "--dir",
    "directory",
    default=None,
    type=str,
    help="Directory to put the algorithm into",
)
def cli_algorithm_update(directory: str) -> dict:
    """Update an algorithm template

    When a new version of the algorithm template is released, you can update
    your existing algorithm template (which you created with
    `v6 algorithm create`) by running this command.
    """
    if not directory:
        default_dir = str(Path(os.getcwd()))
        directory = q.text("Algorithm directory:", default=default_dir).ask()

    run_update(directory, overwrite=True)

    info("Template updated!")
