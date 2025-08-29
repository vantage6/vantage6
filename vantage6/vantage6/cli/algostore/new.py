import click
import questionary as q

from vantage6.common.globals import (
    DEFAULT_API_PATH,
    InstanceType,
    Ports,
)

from vantage6.cli.common.new import new
from vantage6.cli.configuration_wizard import add_common_server_config
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option(
    "-n", "--name", default=None, help="Name of the configuration you want to use."
)
@click.option(
    "--system",
    "system_folders",
    flag_value=True,
    help="Use system folders instead of user folders. This is the default",
)
@click.option(
    "--user",
    "system_folders",
    flag_value=False,
    default=DEFAULT_SERVER_SYSTEM_FOLDERS,
    help="Use user folders instead of system folders",
)
@click.option("--context", default=None, help="Kubernetes context to use")
@click.option(
    "--namespace",
    default=None,
    help="Kubernetes namespace to use",
)
def cli_algo_store_new(
    name: str, system_folders: bool, namespace: str, context: str
) -> None:
    """
    Create a new server configuration.
    """

    new(
        questionnaire_function=algo_store_configuration_questionaire,
        name=name,
        system_folders=system_folders,
        namespace=namespace,
        context=context,
        type_=InstanceType.ALGORITHM_STORE,
    )


def algo_store_configuration_questionaire(instance_name: str) -> dict:
    """
    Questionary to generate a config file for the algorithm store server
    instance.

    Parameters
    ----------
    instance_name : str
        Name of the server instance.

    Returns
    -------
    dict
        Dictionary with the new server configuration
    """
    config = {"store": {}, "database": {}}

    config, is_production = add_common_server_config(
        config, InstanceType.ALGORITHM_STORE, instance_name
    )
    if not is_production:
        config["store"]["dev"] = {
            "host_uri": "host.docker.internal",
            "disable_review": True,
            "review_own_algorithm": True,
        }

    default_v6_server_uri = f"http://localhost:{Ports.DEV_SERVER}{DEFAULT_API_PATH}"
    default_root_username = "admin"

    v6_server_uri = q.text(
        "What is the Vantage6 server linked to the algorithm store? "
        "Provide the link to the server endpoint.",
        default=default_v6_server_uri,
    ).unsafe_ask()

    root_username = q.text(
        "What is the username of the root user?",
        default=default_root_username,
    ).unsafe_ask()

    config["root_user"] = {
        "v6_server_uri": v6_server_uri,
        "username": root_username,
    }

    # ask about openness of the algorithm store
    config["policies"] = {}
    is_open = q.confirm(
        "Do you want to open the algorithm store to the public? This will allow anyone "
        "to view the algorithms, but they cannot modify them.",
        default=False,
    ).unsafe_ask()
    if is_open:
        open_algos_policy = "public"
    else:
        is_open_to_whitelist = q.confirm(
            "Do you want to allow all authenticated users to access "
            "the algorithms in the store? If not allowing this, you will have to assign"
            " the appropriate permissions to each user individually.",
            default=True,
        ).unsafe_ask()
        open_algos_policy = "authenticated" if is_open_to_whitelist else "private"
    config["policies"]["algorithm_view"] = open_algos_policy

    return config
