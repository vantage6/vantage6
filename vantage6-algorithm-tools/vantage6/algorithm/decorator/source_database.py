import os

from functools import wraps
from vantage6.common import error
from vantage6.common.globals import ContainerEnvNames


def source_database(func) -> callable:
    @wraps(func)
    def decorator(*args, mock_uri: str | None = None, **kwargs) -> callable:
        """
        This decorator provides a the source database URI to the function.

        The user can request different databases that correspond to the different data
        sources that are available at each node. This decorator can exclusively be used
        in combination with the `data_extraction` decorator. This is Because this
        decorator relies on certain environment variables, that are only present when
        the method is executed in a container with data-extraction privileges.

        Parameters
        ----------
        mock_uri : str
            Mock URI to use instead of the regular URI
        """
        uri = os.environ.get(ContainerEnvNames.DATABASE_URI.value, mock_uri)
        if uri is None:
            error("No database URI provided. Exiting...")
            exit(1)

        return func(uri, *args, **kwargs)

    return decorator
