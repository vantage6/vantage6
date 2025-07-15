import click
from colorama import Fore, Style

from vantage6.common import ensure_config_dir_writable, error, info
from vantage6.common.globals import InstanceType

from vantage6.cli.config import CliConfig
from vantage6.cli.configuration_wizard import configuration_wizard
from vantage6.cli.context.server import ServerContext
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS
from vantage6.cli.utils import check_config_name_allowed, prompt_config_name


@click.command()
@click.option(
    "-n", "--name", default=None, help="name of the configuration you want to use."
)
@click.option("--system", "system_folders", flag_value=True)
@click.option(
    "--user", "system_folders", flag_value=False, default=DEFAULT_SERVER_SYSTEM_FOLDERS
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_server_new(
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
) -> None:
    """
    Create a new server configuration.
    """
    cli_config = CliConfig()
    context, namespace = cli_config.compare_changes_config(
        context=context,
        namespace=namespace,
    )

    name = prompt_config_name(name)

    # check if name is valid
    check_config_name_allowed(name)

    # check that this config does not exist
    try:
        if ServerContext.config_exists(name, system_folders):
            error(f"Configuration {Fore.RED}{name}{Style.RESET_ALL} already " "exists!")
            exit(1)
    except Exception as e:
        error(e)
        exit(1)

    # Check that we can write in this folder
    if not ensure_config_dir_writable(system_folders):
        error("Your user does not have write access to all folders. Exiting")
        info(
            f"Create a new server using '{Fore.GREEN}v6 server new "
            f"--user{Style.RESET_ALL}' instead!"
        )
        exit(1)

    # create config in ctx location
    try:
        cfg_file = configuration_wizard(InstanceType.SERVER, name, system_folders)
    except KeyboardInterrupt:
        error("Configuration creation aborted.")
        exit(1)
    info(f"New configuration created: {Fore.GREEN}{cfg_file}{Style.RESET_ALL}")

    # info(f"root user created.")
    flag = "" if system_folders else "--user"
    info(
        f"You can start the server by running {Fore.GREEN}v6 server start "
        f"{flag}{Style.RESET_ALL}"
    )
