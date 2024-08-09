from vantage6.common.globals import InstanceType
from vantage6.cli.configuration_wizard import select_configuration_questionaire
from vantage6.cli.context import get_context
from vantage6.cli.context.server import ServerContext


def get_dev_server_context(config: str | None, name: str | None) -> ServerContext:
    """
    Get the server context for the development server.

    Parameters
    ----------
    config : str | None
        Path to the configuration file. If None, the name will be used.
    name : str | None
        Name of the configuration. If None, a questionaire will be shown.
    """
    if config:
        return ServerContext.from_external_config_file(config)
    if not name:
        name = select_configuration_questionaire(
            InstanceType.SERVER, system_folders=False
        )
    return get_context(InstanceType.SERVER, name, system_folders=False)
