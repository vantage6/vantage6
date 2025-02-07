import os
from pathlib import Path

import click
import questionary as q
from copier import run_update
import copier.errors

from vantage6.common import info, warning


@click.command()
@click.option(
    "-d",
    "--dir",
    "directory",
    default=None,
    type=str,
    help="Directory to put the algorithm into",
)
@click.option(
    "--change-answers",
    is_flag=True,
    flag_value=True,
    help="Change answers to questions that were already answered",
    default=False,
)
def cli_algorithm_update(directory: str, change_answers: bool) -> dict:
    """Update an algorithm template

    When a new version of the algorithm template is released, you can update
    your existing algorithm template (which you created with
    `v6 algorithm create`) by running this command.
    """
    if not directory:
        default_dir = str(Path(os.getcwd()))
        try:
            directory = q.text("Algorithm directory:", default=default_dir).unsafe_ask()
        except KeyboardInterrupt:
            info("Aborted by user!")
            return

    info("Updating template...")
    try:
        run_update(
            directory, overwrite=True, skip_answered=not change_answers, unsafe=True
        )
        info("Template updated!")
    except copier.errors.UserMessageError as exc:
        warning(f"Update failed: {exc}")
