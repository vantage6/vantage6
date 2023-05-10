import os

from vantage6.client.algorithm_client import AlgorithmClient
from vantage6.tools.wrappers import (
    CSVWrapper, ExcelWrapper, SparqlDockerWrapper, ParquetWrapper,
    SQLWrapper, OMOPWrapper
)
from vantage6.tools.wrap import load_input
from vantage6.tools.util import info, error


def algorithm_client(func: callable) -> callable:
    """
    Decorator that adds an algorithm client object to a function

    Parameters
    ----------
    func : callable
        Function to decorate

    Returns
    -------
    callable
        Decorated function
    """
    def wrap_function(*args, **kwargs):
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
        print(client)
        return func(client, *args, **kwargs)
    return wrap_function

# usage of the above is something like:
# @algorithm_client
# def my_algorithm(client, *args, **kwargs):
#     client.do_stuff(..)


def data(func: callable) -> callable:
    """
    Decorator that adds algorithm data to a function

    Parameters
    ----------
    label : str
        Label of the database to load
    func : callable
        Function to decorate

    Returns
    -------
    callable
        Decorated function
    """
    def wrap_function(*args, **kwargs):
        # TODO in v4+, we should work with multiple databases instead of this
        # default one. This could be done by passing a list to the envvar below
        # and then looping over it.
        label = os.environ["USER_REQUESTED_DATABASE_LABEL"]
        database_uri = os.environ[f"{label.upper()}_DATABASE_URI"]
        info(f"Using '{database_uri}' as database")

        # Get the database type from the environment variable, this variable is
        # set by the vantage6 node based on its configuration file.
        database_type = os.environ.get(
            f"{label.upper()}_DATABASE_TYPE", "csv").lower()

        # Create the correct wrapper based on the database type, note that the
        # multi database wrapper is not available.
        if database_type == "csv":
            wrapper = CSVWrapper()
        elif database_type == "excel":
            wrapper = ExcelWrapper()
        elif database_type == "sparql":
            wrapper = SparqlDockerWrapper()
        elif database_type == "parquet":
            wrapper = ParquetWrapper()
        elif database_type == "sql":
            wrapper = SQLWrapper()
        elif database_type == "omop":
            wrapper = OMOPWrapper()
        else:
            error(f"Unknown database type '{database_type}' for database with "
                  f"label '{label}'. Please check the node configuration.")
            exit(1)

        # Load the input data from the input file - this may e.g. include the
        # query to execute on the database
        input_file = os.environ["INPUT_FILE"]
        info(f"Reading input file {input_file}")
        input_data = load_input(input_file)

        # Load the data from the database
        data_ = wrapper.load_data(database_uri, input_data)

        return func(data_, *args, **kwargs)
    return wrap_function
