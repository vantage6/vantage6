import click
import questionary
from kubernetes import config

from vantage6.common import error

from vantage6.cli.config import CliConfig
from vantage6.cli.utils import switch_context_and_namespace


@click.command()
@click.argument("context", required=False, type=str, default=None)
def cli_use_context(context: str):
    """
    Set which Kubernetes context to use.
    """
    # Get available contexts
    contexts, active_context = config.list_kube_config_contexts()
    context_names = [ctx["name"] for ctx in contexts]

    # Prompt user to select a context
    if not context:
        current = active_context["name"] if active_context else None
        context = questionary.select(
            "Which Kubernetes context do you want to use?",
            choices=context_names,
            default=current if current in context_names else None,
        ).ask()

        # If no context is selected (e.g. KeyboardInterrupt), exit
        if not context:
            return

    # Load the selected context
    try:
        config.load_kube_config(context=context)
    except Exception:
        error(f"Cannot not find {context} in kube config")
        return

    # Update kubeconfig current-context
    switch_context_and_namespace(context=context)

    # Clear the last_context in CLI config
    cli_config = CliConfig()
    cli_config.remove_kube()
