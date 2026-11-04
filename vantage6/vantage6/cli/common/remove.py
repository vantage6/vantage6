import itertools
import sys
from pathlib import Path
from shutil import rmtree

import questionary as q

from vantage6.common import (
    error,
    info,
)
from vantage6.common.context import AppContext
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    check_running,
    delete_kubernetes_secret,
    referenced_secret_names,
)
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.k8s_config import select_k8s_config
from vantage6.cli.utils import remove_file
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


def execute_remove(
    ctx: AppContext,
    instance_type: InstanceType,
    infra_component: InfraComponentName,
    name: str,
    system_folders: bool,
    force: bool,
) -> None:
    """
    Function to remove a vantage6 service instance.

    Parameters
    ----------
    ctx : AppContext
        App context object
    instance_type : InstanceType
        Type of instance that is checked
    infra_component : InfraComponentName
        The infra component of the service
    name : str
        Name of the instance
    system_folders : bool
        Whether to use system folders or user folders
    force : bool
        Whether to ask for confirmation before removing or not
    """
    if check_running(ctx.helm_release_name, instance_type, name, system_folders):
        error(
            f"The {infra_component.value} {name} is still running! Please stop the "
            f"{infra_component.value} before deleting it."
        )
        sys.exit(1)

    if (
        not force
        and not q.confirm(
            f"This {infra_component.value} will be deleted permanently including its "
            "configuration. Are you sure?",
            default=False,
        ).ask()
    ):
        info(f"The {infra_component.value} {name} will not be deleted")
        sys.exit(0)

    _remove_referenced_secrets(ctx.config, force)

    # remove the config file
    remove_file(ctx.config_file, "configuration")

    # ensure log files are closed before removing
    log_dir = Path(ctx.log_file.parent)
    if log_dir.exists():
        info(f"Removing log directory: {log_dir}")
        for handler in itertools.chain(ctx.log.handlers, ctx.log.root.handlers):
            handler.close()
        # remove the whole folder with all the log files. This may also still contain
        # other files like (for HQ) RabbitMQ configuration etc
        rmtree(log_dir)


def _remove_referenced_secrets(config: dict, force: bool) -> None:
    """
    Delete the Kubernetes secrets that a configuration refers to.

    Unless the removal is forced, the user is asked first, and the secrets are kept by
    default, because deleting e.g. database credentials can make existing data
    inaccessible.

    Parameters
    ----------
    config : dict
        The configuration that is being removed
    force : bool
        Whether to delete the secrets without asking
    """
    names = referenced_secret_names(config)
    if not names:
        return
    info(f"This configuration refers to Kubernetes secrets: {', '.join(names)}")
    if (
        not force
        and not q.confirm(
            "Do you also want to delete these secrets? They cannot be recovered.",
            default=False,
        ).unsafe_ask()
    ):
        info("The Kubernetes secrets are kept.")
        return
    namespace = config.get("namespace")
    k8s_config = select_k8s_config(namespace=namespace)
    namespace = namespace or k8s_config.namespace
    core_api = get_core_api_with_ssl_handling(k8s_config.context)
    for name in names:
        delete_kubernetes_secret(core_api, name, namespace)
        info(f"Deleted Kubernetes secret '{name}' (namespace '{namespace}')")
