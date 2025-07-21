import click
import questionary
from kubernetes import client, config

from vantage6.cli.config import CliConfig
from vantage6.cli.utils import switch_context_and_namespace
from vantage6.common import error


@click.command()
@click.argument("namespace", required=False, type=str, default=None)
def cli_use_namespace(namespace: str):
    """
    Set which Kubernetes namespace to use.

    The namespace will be created if it does not exist.
    """
    # Load the active context configuration
    config.load_kube_config()

    try:
        v1 = client.CoreV1Api()
        namespace_list = v1.list_namespace()
    except Exception:
        error(
            "Failed to connect to Kubernetes cluster. Check if the cluster is running and reachable."
        )
        return

    namespace_names = [ns.metadata.name for ns in namespace_list.items]

    # Prompt user to select a namespace
    if not namespace:
        namespace = questionary.select(
            "Which Kubernetes namespace do you want to use?",
            choices=namespace_names,
        ).ask()

        # If no namespace is selected (e.g. KeyboardInterrupt), exit
        if not namespace:
            return

    # Check if namespace exists, create if not
    if namespace not in namespace_names:
        namespace_body = client.V1Namespace(
            metadata=client.V1ObjectMeta(name=namespace)
        )
        v1.create_namespace(namespace_body)

    # Switch to the selected namespace for current context
    switch_context_and_namespace(namespace=namespace)

    # Remove the last_context in CLI config
    cli_config = CliConfig()
    cli_config.remove_kube()
