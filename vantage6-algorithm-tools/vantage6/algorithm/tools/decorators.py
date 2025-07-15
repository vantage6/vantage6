import os
from pathlib import Path
from functools import wraps
from dataclasses import dataclass

from vantage6.algorithm.tools.util import info, error, warn

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
    dbms: str | None


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


def get_ohdsi_metadata(label: str) -> OHDSIMetaData:
    """
    Retrieve the OHDSI metadata from the environment variables.

    The following environment variables are expected to be set in the
    node configuration in the `env` key of the `database` section:

    ```yaml
    ...
    databases:
      - label: my_database
        type: OMOP
        uri: jdbc:postgresql://host.docker.internal:5454/postgres
        env:
            CDM_DATABASE: "my_user"
            CDM_SCHEMA: "my_password"
            RESULTS_SCHEMA: "my_password"
            DBMS: "postgresql"
    ...
    ```

    In case these are not set, the algorithm execution is terminated.

    Parameters
    ----------
    label : str
        Label of the database to connect to

    Example
    -------
    >>> get_ohdsi_metadata("my_database")
    """
    # check that all node environment variables are set
    expected_env_vars = ("CDM_DATABASE", "CDM_SCHEMA", "RESULTS_SCHEMA", "DBMS")
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
        dbms=os.environ[f"{label_}_DB_PARAM_DBMS"],
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
        error("Did you use 'algorithm-ohdsi-base' image to build this algorithm?")
        exit(1)

    # environment vars are always uppercase
    label_ = label.upper()

    # check that the required environment variables are set
    for var in ("DBMS", "USER", "PASSWORD"):
        _check_environment_var_exists_or_exit(f"{label_}_DB_PARAM_{var}")
    _check_environment_var_exists_or_exit(f"{label_}_DATABASE_URI")

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
