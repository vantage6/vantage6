import os
import json
import jwt

from pathlib import Path
from functools import wraps
from dataclasses import dataclass

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
            # read server address from the environment
            host = os.environ["HOST"]
            port = os.environ["PORT"]
            api_path = os.environ["API_PATH"]

            # read token from the environment
            token_file = os.environ["TOKEN_FILE"]
            info("Reading token")
            with open(token_file) as fp:
                token = fp.read().strip()

            client = AlgorithmClient(token=token, host=host, port=port, path=api_path)
            return func(client, *args, **kwargs)

        # set attribute that this function is wrapped in an algorithm client
        decorator.wrapped_in_algorithm_client_decorator = True
        return decorator

    return protection_decorator


# alias for algorithm_client so that algorithm developers can do
# @algorithm_client instead of @algorithm_client()
algorithm_client = _algorithm_client()


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


def database_connection(types: list[str], include_metadata: bool = True) -> callable:
    """
    Decorator that adds a database connection to a function

    By adding @database_connection to a function, a database connection will
    be added to the front of the argument list. This connection can be used to
    communicate with the database.

    Parameters
    ----------
    types : list[str]
        List of types of databases to connect to. Currently only "OMOP" is
        supported.
    include_metadata : bool
        Whether to include metadata in the function arguments. This metadata
        contains the database name, CDM schema, and results schema. Default is
        True.

    Example
    -------
    For a single OMOP data source:
    >>> @database_connection(types=["OMOP"])
    >>> def my_algorithm(connection: Connection, meta: OHDSIMetaData,
    >>>                  <other arguments>):
    >>>     pass

    In case you have multiple OMOP data sources:
    >>> @database_connection(types=["OMOP", "OMOP"])
    >>> def my_algorithm(connection1: Connection, meta1: OHDSIMetaData,
    >>>                  connection2: Connection, meta2: OHDSIMetaData,
    >>>                  <other arguments>):
    >>>     pass

    In the case you do not want to include the metadata:
    >>> @database_connection(types=["OMOP"], include_metadata=False)
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
            if len(labels) < len(types):
                error(
                    f"User provided {len(labels)} databases, but algorithm "
                    f"requires {len(types)} database connections. Exiting."
                )
                exit(1)
            if len(labels) > len(types):
                warn(
                    f"User provided {len(labels)} databases, but algorithm "
                    f"requires {len(types)} database connections. Using the "
                    f"first {len(types)} databases."
                )

            db_args = []
            # Note: zip will stop at the shortest iterable, so this is exactly
            # what we want in the len(labels) > len(types) case.
            for type_, label in zip(types, labels):
                match type_.upper():
                    case "OMOP":
                        info("Creating OMOP database connection")
                        connection = _create_omop_database_connection(label)
                        db_args.append(connection)
                        if include_metadata:
                            meta = get_ohdsi_metadata(label)
                            db_args.append(meta)
                    # case "FHIR":
                    #     pass

            return func(*db_args, *args, **kwargs)

        return decorator

    return connection_decorator


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
        token_file = os.environ["TOKEN_FILE"]
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
            temporary_directory=Path(os.environ["TEMPORARY_FOLDER"]),
            output_file=Path(os.environ["OUTPUT_FILE"]),
            input_file=Path(os.environ["INPUT_FILE"]),
            token_file=Path(os.environ["TOKEN_FILE"]),
        )
        return func(metadata, *args, **kwargs)

    return decorator


def get_ohdsi_metadata(label: str) -> OHDSIMetaData:
    """
    Retrieve the OHDSI metadata from the environment variables.

    The following environment variables are expected to be set in the
    node configuration in the `env` key of the `database` section:

    - `CDM_DATABASE`
    - `CDM_SCHEMA`
    - `RESULTS_SCHEMA`

    In case these are not set, the algorithm execution is terminated.

    Example
    -------
    >>> get_ohdsi_metadata("my_database")
    """
    # check that all node environment variables are set
    expected_env_vars = ["CDM_DATABASE", "CDM_SCHEMA", "RESULTS_SCHEMA"]
    label_ = label.upper()
    for var in expected_env_vars:
        _check_environment_var_exists_or_exit(f"{label_}_DB_PARAM_{var}")

    tmp = Path(os.environ["TEMPORARY_FOLDER"])
    metadata = OHDSIMetaData(
        database=os.environ[f"{label_}_DB_PARAM_CDM_DATABASE"],
        cdm_schema=os.environ[f"{label_}_DB_PARAM_CDM_SCHEMA"],
        results_schema=os.environ[f"{label_}_DB_PARAM_RESULTS_SCHEMA"],
        incremental_folder=tmp / "incremental",
        cohort_statistics_folder=tmp / "cohort_statistics",
        export_folder=tmp / "export",
    )
    return metadata


def _create_omop_database_connection(label: str) -> callable:
    """
    Create a connection to an OMOP database.

    It expects that the following environment variables are set:
    - DB_PARAM_DBMS: type of database to connect to
    - DB_PARAM_USER: username to connect to the database
    - DB_PARAM_PASSWORD: password to connect to the database

    These should be provided in the vantage6 node configuration file in the
    `database` section without the `DB_PARAM_` prefix. For example:

    ```yaml
    ...
    databases:
      - label: my_database
        type: OMOP
        uri: jdbc:postgresql://host.docker.internal:5454/postgres
        env:
            DBMS: "postgresql"
            USER: "my_user"
            PASSWORD: "my_password"
    ...
    ```

    Parameters
    ----------
    label : str
        Label of the database to connect to

    Returns
    -------
    callable
        OHDSI Database Connection object
    """

    # check that the OHDSI package is available in this container
    if not OHDSI_AVAILABLE:
        error("OHDSI/DatabaseConnector is not available.")
        error("Did you use 'algorithm-ohdsi-base' image to build this " "algorithm?")
        exit(1)

    # environment vars are always uppercase
    label_ = label.upper()

    # check that the required environment variables are set
    for var in ("DBMS", "USER", "PASSWORD"):
        _check_environment_var_exists_or_exit(f"{label_}_DB_PARAM_{var}")

    info("Reading OHDSI environment variables")
    dbms = os.environ[f"{label_}_DB_PARAM_DBMS"]
    uri = os.environ[f"{label_}_DATABASE_URI"]
    user = os.environ[f"{label_}_DB_PARAM_USER"]
    password = os.environ[f"{label_}_DB_PARAM_PASSWORD"]
    info(f" - dbms: {dbms}")
    info(f" - uri: {uri}")
    info(f" - user: {user}")

    info("Creating OHDSI database connection")
    return connect_to_omop(
        dbms=dbms, connection_string=uri, password=password, user=user
    )


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
    # Load the input data from the input file - this may e.g. include the
    database_uri = os.environ[f"{label.upper()}_DATABASE_URI"]
    info(f"Using '{database_uri}' with label '{label}' as database")

    # Get the database type from the environment variable, this variable is
    # set by the vantage6 node based on its configuration file.
    database_type = os.environ.get(f"{label.upper()}_DATABASE_TYPE", "csv").lower()

    # Load the data based on the database type. Try to provide environment
    # variables that should be available for some data types.
    return load_data(
        database_uri,
        database_type,
        query=os.environ.get(f"{label.upper()}_QUERY"),
        sheet_name=os.environ.get(f"{label.upper()}_SHEET_NAME"),
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
