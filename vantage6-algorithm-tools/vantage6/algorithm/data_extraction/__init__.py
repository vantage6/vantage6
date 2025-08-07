import io
import os

import pandas as pd
from SPARQLWrapper import CSV, SPARQLWrapper
from sqlalchemy import create_engine

from vantage6.common import error, info

from vantage6.algorithm.tools.exceptions import DataReadError

from vantage6.algorithm.decorator.action import data_extraction

_SPARQL_RETURN_FORMAT = CSV


@data_extraction
def read_csv(connection_details: dict) -> pd.DataFrame:
    """
    Extract data from a CSV database to yield a dataframe.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the database connection details.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the CSV file.

    Raises
    ------
    DataReadError
        If the CSV file cannot be read.
    """
    return _read_csv(connection_details)


def _read_csv(connection_details: dict) -> pd.DataFrame:
    info(f"Reading CSV file from {connection_details['uri']}")

    try:
        df = pd.read_csv(connection_details["uri"])
    except FileNotFoundError as e:
        error(f"File not found: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"File not found: {e}")
    except Exception as e:
        error(f"Error reading CSV file: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"Error reading CSV file: {e}")
    return df


@data_extraction
def read_parquet(connection_details: dict) -> pd.DataFrame:
    """
    Extract data from a Parquet database to yield a dataframe.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the database connection details.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the Parquet file.

    Raises
    ------
    DataReadError
        If the Parquet file cannot be read.
    """
    return _read_parquet(connection_details)


def _read_parquet(connection_details: dict) -> pd.DataFrame:
    info(f"Reading Parquet file from {connection_details['uri']}")
    try:
        df = pd.read_parquet(connection_details["uri"])
    except FileNotFoundError as e:
        error(f"File not found: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"File not found: {e}")
    except Exception as e:
        error(f"Error reading Parquet file: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"Error reading Parquet file: {e}")
    return df


@data_extraction
def read_excel(connection_details: dict, sheet_name: str | None = None) -> pd.DataFrame:
    """
    Extract data from an Excel database to yield a dataframe.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the database connection details.
    sheet_name : str | None, optional
        Name of the sheet to read from the Excel file. If None, the first sheet is read.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the Excel file.

    Raises
    ------
    DataReadError
        If the Excel file cannot be read or the sheet name is not found.
    """
    return _read_excel(connection_details, sheet_name)


def _read_excel(
    connection_details: dict, sheet_name: str | None = None
) -> pd.DataFrame:
    info(f"Reading Excel file from {connection_details['uri']}")
    if sheet_name:
        info(f"Selecting sheet: {sheet_name}")
    else:
        # Default to the first sheet
        info("No sheet name provided, defaulting to the first sheet")
        sheet_name = 0

    try:
        df = pd.read_excel(connection_details["uri"], sheet_name=sheet_name)
    except FileNotFoundError as e:
        error(f"File not found: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"File not found: {e}")
    except Exception as e:
        error(f"Error reading Excel file: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"Error reading Excel file: {e}")
    return df


@data_extraction
def read_sparql_database(connection_details: dict, query: str) -> pd.DataFrame:
    """
    Extract data from a SPARQL database to yield a dataframe.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the database connection details.
    query : str
        SPARQL query to execute.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the SPARQL query.

    Raises
    ------
    DataReadError
        If the SPARQL query cannot be executed.
    """
    return _read_sparql_database(connection_details, query)


def _read_sparql_database(connection_details: dict, query: str) -> pd.DataFrame:
    info(f"Reading SPARQL data from {connection_details['uri']}")
    sparql = SPARQLWrapper(
        connection_details["uri"], returnFormat=_SPARQL_RETURN_FORMAT
    )
    sparql.setQuery(query)
    result = sparql.query().convert().decode()

    try:
        df = pd.read_csv(io.StringIO(result))
    except Exception as e:
        error(f"Error reading SPARQL data: {e}")
        # pylint: disable=raise-missing-from
        raise DataReadError(f"Error reading SPARQL data: {e}")
    return df


def _sqldb_uri_preprocess(database_uri: str) -> str:
    """
    Transforms the URI of a file-based/embedded RDBMS on a fully-qualified one, when
    this URI follows the convention /<file system path>/<dbname>.<supported db type>.
    When these conditions are not met, the original URI is returned.

    Pre-condition:
    - the database_uri, if a file-based-one, should exist (this is already validated
    when the node boots up)

    Parameters:
    ----------
    database_uri : str
        The URI of the database file.

    Returns
    -------
    str
        A fully-qualified URI compatible with the database type or the original string
        if no match found.
    """

    # Mapping between file extensions and embedded db URIs.
    # Other embedded DB would be included when its support
    # is validated (e.g., H2)
    embedded_db_extensions = {"sqlite": "sqlite:///{0}"}

    # Check if the URI is a unix-absolute file path
    if (os.path.isabs(database_uri)) and not database_uri.endswith("/"):
        database_extension = database_uri.split("/")[-1].split(".")[-1]

        for supported_db_extension, uri_format in embedded_db_extensions.items():
            if supported_db_extension == database_extension:
                # Format the SQLalchemy URI using the database_path and the
                # corresponding URI format
                return uri_format.format(database_uri)
        # Return the original string if no matching extension found
        return database_uri
    else:
        # Return the original string if the URI is not an absolute unix file path
        return database_uri


@data_extraction
def read_sql_database(connection_details: dict, query: str) -> pd.DataFrame:
    """
    Extract data from a SQL database to yield a dataframe.

    Parameters
    ----------
    connection_details : dict
        Dictionary containing the database connection details.
    query : str
        SQL query to execute.

    Returns
    -------
    pd.DataFrame
        DataFrame containing the data from the SQL query.

    Raises
    ------
    DataReadError
        If the SQL query cannot be executed.
    """
    return _read_sql_database(connection_details, query)


def _read_sql_database(connection_details: dict, query: str) -> pd.DataFrame:
    info(f"Reading SQL data from {connection_details['uri']}")
    engine = create_engine(_sqldb_uri_preprocess(connection_details["uri"]))

    dbapi_conn = engine.raw_connection()

    try:
        # Execute the query and store the results in a DataFrame
        df = pd.read_sql_query(query, con=dbapi_conn)

    finally:
        dbapi_conn.close()  # Ensure the connection is closed

    return df
