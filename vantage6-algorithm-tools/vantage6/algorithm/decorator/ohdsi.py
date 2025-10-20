import os
from dataclasses import dataclass
from functools import wraps
from pathlib import Path

from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.util import error, info

from vantage6.algorithm.decorator.action import data_extraction

OHDSI_AVAILABLE = True
try:
    from ohdsi.database_connector import connect as connect_to_omop
except ImportError:
    OHDSI_AVAILABLE = False


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


def omop_data_extraction(include_metadata: bool = True) -> callable:
    """
    Decorator that adds an OMOP database connection to a function

    By adding `@omop_data_extraction` to a function, an OMOP database connection will
    be added to the front of the argument list. This connection object is the
    OHDSI DatabaseConnector object.

    It expects that the following connection details are set in the node configuration:
    - uri: URI to connect to the database
    - dbms: type of database to connect to
    - user: username to connect to the database
    - password: password to connect to the database
    - cdm_database: name of the CDM database
    - cdm_schema: name of the CDM schema
    - results_schema: name of the results schema

    These should be provided in the vantage6 node configuration file in the
    `database`. For example:

    ```yaml
    ...
    databases:
      - label: my_database
        type: OMOP
        uri: jdbc:postgresql://my_host:5454/postgres
        env:
            DBMS: "postgresql"
            USER: "my_user"
            PASSWORD: "my_password"
            CDM_DATABASE: "my_user"
            CDM_SCHEMA: "my_schema"
            RESULTS_SCHEMA: "my_results_schema"
    ...
    ```

    Parameters
    ----------
    include_metadata : bool
        Whether to include metadata in the function arguments. This metadata
        contains the database name, CDM schema, and results schema. Default is
        True.

    Example
    -------
    >>> @omop_data_extraction
    >>> def my_algorithm(connection: RS4, meta: OHDSIMetaData,
    >>>                  <other arguments>):
    >>>     pass

    In the case you do not want to include the metadata, you can set the
    `include_metadata` argument to False.

    >>> @omop_data_extraction(include_metadata=False)
    >>> def my_algorithm(connection: RS4, <other arguments>):
    >>>     pass
    """

    def connection_decorator(func: callable, *args, **kwargs) -> callable:
        @wraps(func)
        @data_extraction
        def decorator(*args, connection_details: dict, **kwargs) -> callable:
            """
            Wrap the function with the database connection
            """
            connection = _create_omop_database_connection(connection_details)
            if include_metadata:
                metadata = _get_ohdsi_metadata(connection_details)
                return func(connection, metadata, *args, **kwargs)
            else:
                return func(connection, *args, **kwargs)

        return decorator

    return connection_decorator


def _create_omop_database_connection(connection_details: dict) -> callable:
    """
    Create a connection to an OMOP database.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the connection details

    Returns
    -------
    callable
        OHDSI Database Connection object
    """

    # check that the OHDSI package is available in this container
    if not OHDSI_AVAILABLE:
        error("OHDSI/DatabaseConnector is not available.")
        error("Did you use 'algorithm-ohdsi-base' image to build this algorithm?")
        exit(1)

    expected_keys = ["dbms", "uri", "user", "password"]
    if not set(expected_keys).issubset(connection_details):
        missing_keys = set(expected_keys) - set(connection_details)
        error(f"Missing connection details: {missing_keys}. Exiting...")
        exit(1)

    info("Creating OHDSI database connection")
    dbms = connection_details["dbms"]
    uri = connection_details["uri"]
    user = connection_details["user"]
    password = connection_details["password"]
    info(f" - dbms: {dbms}")
    info(f" - uri: {uri}")
    info(f" - user: {user}")

    info("Creating OHDSI database connection")
    return connect_to_omop(
        dbms=dbms, connection_string=uri, password=password, user=user
    )


def _get_ohdsi_metadata(connection_details: dict) -> OHDSIMetaData:
    """
    Collect the OHDSI metadata and store it in a dataclass.

    In there are missing OMOP database connection details, the algorithm execution is
    terminated.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the connection details

    Example
    -------
    >>> _get_ohdsi_metadata({
    >>>     "cdm_database": "my_database",
    >>>     "cdm_schema": "my_schema",
    >>>     "results_schema": "my_results_schema",
    >>>     "dbms": "postgresql",
    >>> })
    """
    # check that all node environment variables are set
    expected_env_vars = set("cdm_database", "cdm_schema", "results_schema", "dbms")
    if not expected_env_vars.issubset(connection_details):
        missing_env_vars = expected_env_vars - connection_details
        error(f"Missing connection details: {missing_env_vars}")
        error("Exiting...")
        exit(1)

    tmp = Path(os.environ[ContainerEnvNames.SESSION_FOLDER.value])
    metadata = OHDSIMetaData(
        database=connection_details["cdm_database"],
        cdm_schema=connection_details["cdm_schema"],
        results_schema=connection_details["results_schema"],
        incremental_folder=tmp / "incremental",
        cohort_statistics_folder=tmp / "cohort_statistics",
        export_folder=tmp / "export",
        dbms=connection_details["dbms"],
    )
    return metadata
