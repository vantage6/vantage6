from typing import Any

import click
import questionary as q

from vantage6.common.globals import (
    InstanceType,
)

from vantage6.cli.common.new import new
from vantage6.cli.globals import DEFAULT_SERVER_SYSTEM_FOLDERS


@click.command()
@click.option(
    "-n", "--name", default=None, help="name of the configuration you want to use."
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
def cli_auth_new(
    name: str,
    system_folders: bool,
    namespace: str,
    context: str,
) -> None:
    """
    Create a new server configuration.
    """
    new(
        questionnaire_function=auth_configuration_questionaire,
        name=name,
        system_folders=system_folders,
        namespace=namespace,
        context=context,
        type_=InstanceType.AUTH,
    )


def auth_configuration_questionaire(instance_name: str) -> dict[str, Any]:
    """
    Kubernetes-specific questionnaire to generate Helm values for the Keycloak helm
    chart.
    """
    config = {"keycloak": {}}

    is_production = q.confirm(
        "Do you want to use production settings? If not, the service will be configured"
        " to be more suitable for development or testing purposes.",
        default=True,
    ).unsafe_ask()

    config["keycloak"]["production"] = is_production

    if is_production:
        ui_url = q.text(
            "Please provide the URL of the UI. This is the URL that users will use to "
            "log in to the service.",
            default="https://ui.vantage6.ai",
        ).unsafe_ask()
        # add http://localhost:7681 as that is used by the Python client
        config["keycloak"]["redirectUris"] = [ui_url, "http://localhost:7681"]

    return config
