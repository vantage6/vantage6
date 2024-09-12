import os
import json
import jwt

from pathlib import Path
from functools import wraps
from dataclasses import dataclass

import pandas as pd

from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.client import AlgorithmClient
from vantage6.algorithm.tools.mock_client import MockAlgorithmClient
from vantage6.algorithm.tools.util import info, error, warn


@dataclass
class RunMetaData:
    """Dataclass containing metadata of the run."""

    task_id: int | None
    node_id: int | None
    collaboration_id: int | None
    organization_id: int | None
    temporary_directory: Path | None
    output_file: Path | None
    input_file: Path | None
    token_file: Path | None


@dataclass
class OHDSIMetaData:
    """Dataclass containing metadata of the OMOP database."""

    database: str | None
    cdm_schema: str | None
    results_schema: str | None
    incremental_folder: Path | None
    cohort_statistics_folder: Path | None
    export_folder: Path | None
    dbms: str | None


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
            *args, mock_client: MockAlgorithmClient = None, **kwargs
        ) -> callable:
            """
            Wrap the function with the client object

            Parameters
            ----------
            mock_client : MockAlgorithmClient
                Mock client to use instead of the regular client
            """
            if mock_client is not None:
                return func(mock_client, *args, **kwargs)

            # read token from the environment
            token_file = os.environ.get(ContainerEnvNames.TOKEN_FILE.value)
            if not token_file:
                error(
                    "Token file not found. Are you running a `compute` container? "
                    "Exiting..."
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


def data(number_of_databases: int = 1) -> callable:
    """
    Decorator that adds algorithm data to a function

    By adding `@data()` to a function, one or several pandas dataframes will be
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
        def decorator(
            *args, mock_data: list[pd.DataFrame] = None, **kwargs
        ) -> callable:
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
                error(
                    f"Algorithm requires {number_of_databases} databases "
                    f"but only {len(labels)} were provided. "
                    "Exiting..."
                )
                exit(1)
            elif len(labels) > number_of_databases:
                warn(
                    f"Algorithm requires only {number_of_databases} databases"
                    f", but {len(labels)} were provided. Using the "
                    f"first {number_of_databases} databases."
                )

            for i in range(number_of_databases):

                label = labels[i]
                # read the data from the database
                info("Reading Dataframe")
                data_ = _get_data_from_label(label)

                # add the data to the arguments
                args = (data_, *args)

            return func(*args, **kwargs)

        # set attribute that this function is wrapped in a data decorator
        decorator.wrapped_in_data_decorator = True
        return decorator

    return protection_decorator


def metadata(func: callable) -> callable:
    @wraps(func)
    def decorator(*args, **kwargs) -> callable:
        """
        Decorator the function with metadata from the run.

        Decorator that adds metadata from the run to the function. This
        includes the task id, node id, collaboration id, organization id,
        temporary directory, output file, input file, and token file.

        Example
        -------
        >>> @metadata
        >>> def my_algorithm(metadata: RunMetaData, <other arguments>):
        >>>     pass
        """
        token_file = os.environ[ContainerEnvNames.TOKEN_FILE.value]
        info("Reading token")
        with open(token_file) as fp:
            token = fp.read().strip()

        info("Extracting payload from token")
        payload = _extract_token_payload(token)

        metadata = RunMetaData(
            task_id=payload["task_id"],
            node_id=payload["node_id"],
            collaboration_id=payload["collaboration_id"],
            organization_id=payload["organization_id"],
            temporary_directory=Path(
                os.environ[ContainerEnvNames.SESSION_FOLDER.value]
            ),
            output_file=Path(os.environ[ContainerEnvNames.OUTPUT_FILE.value]),
            input_file=Path(os.environ[ContainerEnvNames.INPUT_FILE.value]),
            token_file=Path(os.environ[ContainerEnvNames.TOKEN_FILE.value]),
        )
        return func(metadata, *args, **kwargs)

    return decorator


def _check_environment_var_exists_or_exit(var: str):
    """
    Check if the environment variable 'var' exists or print and exit.

    Parameters
    ----------
    var : str
        Environment variable name to check
    """
    if var not in os.environ:
        error(f"Environment variable '{var}' is not set. Exiting...")
        exit(1)


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
    # Load the dataframe by the user specified handle. The dataframes are always stored
    # in the session folder, which is set by the vantage6 node. The label is the name of
    # the dataframe file, which is set by the user when creating the task.
    dataframe_file = os.environ[ContainerEnvNames.SESSION_FOLDER.value]
    dataframe_uri = os.path.join(dataframe_file, f"{label}.parquet")
    info(f"Using '{dataframe_uri}' with label '{label}' as database")

    return pd.read_parquet(dataframe_uri)


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
    labels = os.environ[ContainerEnvNames.USER_REQUESTED_DATAFRAME_HANDLES.value]
    return labels.split(",")


def _extract_token_payload(token: str) -> dict:
    """
    Extract the payload from the token.

    Parameters
    ----------
    token: str
        The token as a string.

    Returns
    -------
    dict
        The payload as a dictionary. It contains the keys: `client_type`,
        `node_id`, `organization_id`, `collaboration_id`, `task_id`, `image`,
        and `databases`.
    """
    jwt_payload = jwt.decode(token, options={"verify_signature": False})
    return jwt_payload["sub"]
