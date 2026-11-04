import sys

import click
import questionary as q
from kubernetes.client.exceptions import ApiException
from urllib3.exceptions import HTTPError

from vantage6.common import ensure_config_dir_writable, error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.common.utils import (
    extract_name_and_is_sandbox,
    update_kubernetes_secret,
)
from vantage6.cli.configuration_create import (
    NodeConfigurationManager,
    select_configuration_questionnaire,
)
from vantage6.cli.context.node import NodeContext
from vantage6.cli.globals import DEFAULT_NODE_SYSTEM_FOLDERS as N_FOL
from vantage6.cli.utils_kubernetes import get_core_api_with_ssl_handling


@click.command()
@click.option("-n", "--name", default=None, help="Configuration name")
@click.option("--api-key", default=None, help="New API key")
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Search for configuration in system folders rather than user folders",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=N_FOL,
    help="Search for configuration in user folders rather than "
    "system folders. This is the default",
)
@click.option("--sandbox/--no-sandbox", "is_sandbox", default=False)
@click.option(
    "--context",
    default=None,
    help="Kubernetes context of the node secret. Defaults to the current context",
)
def cli_node_set_api_key(
    name: str,
    api_key: str,
    system_folders: bool,
    is_sandbox: bool,
    context: str | None,
) -> None:
    """
    Set a new API key for the node.

    If the node configuration refers to a Kubernetes secret, the API key is updated
    in that secret. Otherwise, it is written to the configuration file.
    """
    name, is_sandbox = extract_name_and_is_sandbox(name, is_sandbox)
    if is_sandbox:
        system_folders = False
    # select node name
    if not name:
        try:
            name = select_configuration_questionnaire(
                InstanceType.NODE, system_folders, is_sandbox
            )
        except FileNotFoundError:
            error("No configurations could be found!")
            sys.exit(1)

    # Check that we can write in the config folder
    if not ensure_config_dir_writable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        sys.exit(1)

    if not api_key:
        try:
            api_key = q.text("Please enter your new API key:").unsafe_ask()
        except KeyboardInterrupt:
            error("API key input aborted.")
            sys.exit(1)

    ctx = NodeContext(name, system_folders=system_folders, is_sandbox=is_sandbox)
    secret_name = ctx.config["node"].get("existingSecret")
    if secret_name:
        namespace = ctx.config.get("namespace", "default")
        try:
            update_kubernetes_secret(
                get_core_api_with_ssl_handling(context),
                secret_name,
                namespace,
                {"V6_API_KEY": api_key},
            )
        except (RuntimeError, ApiException, HTTPError) as exc:
            error(f"Failed to update the API key in Kubernetes secret: {exc}")
            sys.exit(1)
        info(
            f"Your new API key has been stored in Kubernetes secret '{secret_name}' "
            f"(namespace '{namespace}'). Restart the node to use it."
        )
        return

    # get configuration manager
    conf_mgr = NodeConfigurationManager.from_file(
        ctx.config_file, is_sandbox=is_sandbox
    )

    # set new api key, and save the file
    ctx.config["node"]["apiKey"] = api_key
    conf_mgr.put(ctx.config)
    conf_mgr.save(ctx.config_file)
    info(f"Your new API key has been uploaded to the config file {ctx.config_file}.")
