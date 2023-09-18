import json
import os
from functools import wraps

import pandas as pd


from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
from vantage6.algorithm.tools.util import info, error, warn
from vantage6.algorithm.tools.wrappers import load_data
from vantage6.algorithm.tools.preprocessing import preprocess_data


def algorithm_client(func: callable) -> callable:
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
    """
    def wrap_function(*args, mock_client: MockAlgorithmClient = None,
                      **kwargs) -> callable:
        """
        Wrap the function with the client object

        Parameters
        ----------
        mock_client : MockAlgorithmClient
            Mock client to use instead of the regular client
        """
        if mock_client is not None:
            return func(mock_client, *args, **kwargs)
        # read server address from the environment
        host = os.environ["HOST"]
        port = os.environ["PORT"]
        api_path = os.environ["API_PATH"]

        # read token from the environment
        token_file = os.environ["TOKEN_FILE"]
        info("Reading token")
        with open(token_file) as fp:
            token = fp.read().strip()

        client = AlgorithmClient(token=token, host=host, port=port,
                                 path=api_path)
        return func(client, *args, **kwargs)
    # set attribute that this function is wrapped in an algorithm client
    wrap_function.wrapped_in_algorithm_client_decorator = True
    return wrap_function


def data(number_of_databases: int = 1) -> callable:
    """
    Decorator that adds algorithm data to a function

    By adding @data to a function, one or several pandas dataframes will be
    added to the front of the argument list. This data will be read from the
    databases that the user who creates the task provides.

    Note that the user should provide exactly as many databases as the
    decorated function requires when they create the task.

    There is one reserved argument `mock_data` in the function to be
    decorated. If this argument is provided, the decorator will add this
    mocked data to the front of the argument list, instead of reading in the
    data from the databases.

    Parameters
    ----------
    number_of_databases: int
        Number of data sources to load. These will be loaded in order by which
        the user provided them. Default is 1.

    Returns
    -------
    callable
        Decorated function

    Examples
    --------
    >>> @data(number_of_databases=2)
    >>> def my_algorithm(first_df: pd.DataFrame, second_df: pd.DataFrame,
    >>>                  <other arguments>):
    >>>     pass
    """
    def protection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        def decorator(*args, mock_data: list[pd.DataFrame] = None,
                      **kwargs) -> callable:
            """
            Wrap the function with the data

            Parameters
            ----------
            mock_data : list[pd.DataFrame]
                Mock data to use instead of the regular data
            """
            if mock_data is not None:
                return func(*mock_data, *args, **kwargs)
            # query to execute on the database
            input_file = os.environ["INPUT_FILE"]
            info(f"Reading input file {input_file}")

            # read the labels that the user requested, which is a comma
            # separated list of labels.
            labels = os.environ["USER_REQUESTED_DATABASE_LABELS"]
            labels = labels.split(',')

            # check if user provided enough databases
            if len(labels) < number_of_databases:
                error(f"User provided {len(labels)} databases, but algorithm "
                      f"requires {number_of_databases} databases. Exiting...")
                exit(1)
            elif len(labels) > number_of_databases:
                warn(f"User provided {len(labels)} databases, but algorithm "
                     f"requires {number_of_databases} databases. Using the "
                     f"first {number_of_databases} databases.")

            for i in range(number_of_databases):
                label = labels[i]
                # read the data from the database
                info("Reading data from database")
                data_ = _get_data_from_label(label)

                # do any data preprocessing here
                info(f"Applying preprocessing for database '{label}'")
                env_prepro = os.environ.get(f"{label.upper()}_PREPROCESSING")
                if env_prepro is not None:
                    preprocess = json.loads(env_prepro)
                    data_ = preprocess_data(data_, preprocess)

                # add the data to the arguments
                args = (data_, *args)

            return func(*args, **kwargs)
        # set attribute that this function is wrapped in a data decorator
        decorator.wrapped_in_data_decorator = True
        return decorator
    return protection_decorator


def _get_data_from_label(label: str) -> pd.DataFrame:
    """
    Load data from a database based on the label

    Parameters
    ----------
    label : str
        Label of the database to load

    Returns
    -------
    pd.DataFrame
        Data from the database
    """
    # Load the input data from the input file - this may e.g. include the
    database_uri = os.environ[f"{label.upper()}_DATABASE_URI"]
    info(f"Using '{database_uri}' with label '{label}' as database")

    # Get the database type from the environment variable, this variable is
    # set by the vantage6 node based on its configuration file.
    database_type = os.environ.get(
        f"{label.upper()}_DATABASE_TYPE", "csv").lower()

    # Load the data based on the database type. Try to provide environment
    # variables that should be available for some data types.
    return load_data(
        database_uri,
        database_type,
        query=os.environ.get(f"{label.upper()}_QUERY"),
        sheet_name=os.environ.get(f"{label.upper()}_SHEET_NAME")
    )
