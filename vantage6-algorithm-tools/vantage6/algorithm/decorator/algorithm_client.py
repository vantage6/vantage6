import os

from functools import wraps

from vantage6.common.globals import ContainerEnvNames
from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
from vantage6.algorithm.tools.util import info, error


def _algorithm_client() -> callable:
    """
    Decorator that adds an algorithm client object to a function

    By adding @algorithm_client to a function, the ``algorithm_client``
    argument will be added to the front of the argument list. This client can
    be used to communicate with the server.

    There is one reserved argument `mock_client` in the function to be
    decorated. If this argument is provided, the decorator will add this
    MockAlgorithmClient to the front of the argument list instead of the
    regular AlgorithmClient.

    Parameters
    ----------
    func : callable
        Function to decorate

    Returns
    -------
    callable
        Decorated function

    Examples
    --------
    >>> @algorithm_client
    >>> def my_algorithm(algorithm_client: AlgorithmClient, <other arguments>):
    >>>     pass
    """

    def protection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        def decorator(
            *args, mock_client: MockAlgorithmClient | None = None, **kwargs
        ) -> callable:
            """
            Wrap the function with the client object

            Parameters
            ----------
            mock_client : MockAlgorithmClient | None
                Mock client. If not None, used instead of the regular client
            """
            if mock_client is not None:
                return func(mock_client, *args, **kwargs)

            # read token from the environment
            token_file = os.environ.get(ContainerEnvNames.TOKEN_FILE.value)
            if not token_file:
                error(
                    "Token file not found. Is the method you called started as a "
                    "compute container? Exiting..."
                )
                exit(1)

            info("Reading token")
            with open(token_file) as fp:
                token = fp.read().strip()

            # read server address from the environment
            host = os.environ[ContainerEnvNames.HOST.value]
            port = os.environ[ContainerEnvNames.PORT.value]
            api_path = os.environ[ContainerEnvNames.API_PATH.value]

            client = AlgorithmClient(token=token, host=host, port=port, path=api_path)
            return func(client, *args, **kwargs)

        # set attribute that this function is wrapped in an algorithm client
        decorator.wrapped_in_algorithm_client_decorator = True
        return decorator

    return protection_decorator


# alias for algorithm_client so that algorithm developers can do
# @algorithm_client instead of @algorithm_client()
algorithm_client = _algorithm_client()
