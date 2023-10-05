import json
import os
from functools import wraps

import pandas as pd


from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
from vantage6.algorithm.tools.util import info, error, warn
from vantage6.algorithm.tools.wrappers import load_data
from vantage6.algorithm.tools.preprocessing import preprocess_data

OHDSI_AVAILABLE = True
try:
    from ohdsi.database_connector import connect as connect_to_omop
except ImportError:
    OHDSI_AVAILABLE = False


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

            # read the labels that the user requested
            labels = _get_user_database_labels()

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


def database_connection(type: str) -> callable:
    """

    Example
    -------
    >>> @database_connection(type="OMOP")
    >>> def my_algorithm(connection: Connection, <other arguments>):
    >>>     pass
    """
    def connection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        def decorator(*args, **kwargs) -> callable:
            """
            Wrap the function with the database connection
            """
            labels = _get_user_database_labels()
            if len(labels) != 1:
                error(f"User provided {len(labels)} databases, but algorithm "
                      f"requires 1 database connection. Exiting...")
                exit(1)

            match type:
                case "OMOP":
                    info("Creating OMOP database connection")
                    connection = _create_omop_database_connection(labels[0])
                # case "FHIRE":
                #     connection = _create_fhire_database_connection()

            return func(connection, *args, **kwargs)

        return decorator
    return connection_decorator


def _create_omop_database_connection(label) -> callable:

    # check that the OHDSI package is available in this container
    if not OHDSI_AVAILABLE:
        error("OHDSI/DatabaseConnector is not available.")
        error("Did you use the correct algorithm-base image to "
              "build this algorithm?")
        exit(1)

    info("Reading OHDSI environment variables")
    # TODO these are not actually supplied by the node yet...
    dbms = os.environ["OMOP_DBMS"]
    uri = os.environ[f"{label.upper()}_DATABASE_URI"]
    user = os.environ["OMOP_USER"]
    password = os.environ["OMOP_PASSWORD"]
    info(f' - dbms: {dbms}')
    info(f' - uri: {uri}')
    info(f' - user: {user}')

    info("Creating connection object")
    return connect_to_omop(dbms=dbms, connection_string=uri, password=password,
                           user=user)


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


def _get_user_database_labels() -> list[str]:
    """
    Get the database labels from the environment

    Returns
    -------
    list[str]
        List of database labels
    """
    # read the labels that the user requested, which is a comma
    # separated list of labels.
    labels = os.environ["USER_REQUESTED_DATABASE_LABELS"]
    return labels.split(',')
