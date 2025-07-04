import click
from vantage6.common import info
from vantage6.cli.config import CliConfig
from vantage6.cli.globals import ChartType


@click.command()
@click.option("--auth", type=str, help="Set the path for the auth chart")
@click.option("--node", type=str, help="Set the path for the node chart")
@click.option("--server", type=str, help="Set the path for the server chart")
@click.option("--store", type=str, help="Set the path for the store chart")
def cli_use_chart(auth: str, node: str, server: str, store: str):
    """
    Set which Helm chart to use for CLI operations.
    """
    cli_config = CliConfig()

    # Create a mapping of chart types to their provided values
    chart_options = {
        ChartType.AUTH: auth,
        ChartType.NODE: node,
        ChartType.SERVER: server,
        ChartType.STORE: store,
    }

    # Check if any chart type options were provided
    provided_options = {
        chart_type: chart_path
        for chart_type, chart_path in chart_options.items()
        if chart_path is not None
    }

    # If specific chart type options were provided, set them
    if provided_options:
        for chart_type, chart_path in provided_options.items():
            cli_config.set_default_chart(chart_path, chart_type.value)
        return

    # If no arguments or options provided, print out the default charts
    for chart_type in ChartType:
        default_chart = cli_config.get_default_chart(chart_type.value)
        info(f"Using {chart_type.value:<6} chart: {default_chart}")
