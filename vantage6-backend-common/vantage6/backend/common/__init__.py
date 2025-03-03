"""Common functionality for the vantage6 server and algorithm store."""

from vantage6.common.globals import DEFAULT_API_PATH

# make sure the version is available
from vantage6.backend.common._version import __version__  # noqa: F401


def get_server_url(
    config: dict, server_url_from_request: str | None = None
) -> str | None:
    """ "
    Get the server url from the request data, or from the configuration if it is
    not present in the request.

    Parameters
    ----------
    config : dict
        Server configuration
    server_url_from_request : str | None
        Server url from the request data.

    Returns
    -------
    str | None
        The server url
    """
    if server_url_from_request:
        return server_url_from_request
    server_url = config.get("server_url")
    # make sure that the server url ends with the api path
    api_path = config.get("api_path", DEFAULT_API_PATH)
    if server_url and not server_url.endswith(api_path):
        server_url = server_url + api_path
    return server_url
