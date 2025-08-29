import itertools
from pathlib import Path
from shutil import rmtree

import questionary as q

from vantage6.common import (
    error,
    info,
)
from vantage6.common.context import AppContext
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import check_running
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.utils import remove_file


def execute_remove(
    ctx: AppContext,
    instance_type: InstanceType,
    infra_component: InfraComponentName,
    name: str,
    system_folders: bool,
    force: bool,
) -> None:
    if check_running(ctx.helm_release_name, instance_type, name, system_folders):
        error(
            f"The {infra_component.value} {name} is still running! Please stop the "
            f"{infra_component.value} before deleting it."
        )
        exit(1)

    if not force:
        if not q.confirm(
            f"This {infra_component.value} will be deleted permanently including its "
            "configuration. Are you sure?",
            default=False,
        ).ask():
            info(f"The {infra_component.value} {name} will not be deleted")
            exit(0)

    # remove the config file
    remove_file(ctx.config_file, "configuration")

    # ensure log files are closed before removing
    log_dir = Path(ctx.log_file.parent)
    if log_dir.exists():
        info(f"Removing log directory: {log_dir}")
        for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
            handler.close()
        # remove the whole folder with all the log files. This may also still contain
        # other files like (for the server) RabbitMQ configuration etc
        rmtree(log_dir)
