"""
This module contains algorithm wrappers. These wrappers are used to provide
different data adapters to the algorithms. This way we ony need to write the
algorithm once and can use it with different data adapters.

Currently the following wrappers are available:
    - ``DockerWrapper`` (= ``CSVWrapper``)
    - ``SparqlDockerWrapper``
    - ``ParquetWrapper``
    - ``SQLWrapper``
    - ``ExcelWrapper``

When writing the Docker file for the algorithm, the correct wrapper will
automatically be selected based on the database type. The database type is set
by the vantage6 node based on its configuration file.
"""

from __future__ import annotations
import io
import os
import pandas as pd

from sqlalchemy import create_engine
from enum import Enum
from SPARQLWrapper import SPARQLWrapper, CSV

from vantage6.algorithm.tools.util import info, error

_SPARQL_RETURN_FORMAT = CSV


class DatabaseType(str, Enum):
    """
    Enum for the different database types.

    Attributes
    ----------
    CSV : str
        CSV database
    SQL : str
        SQL database
    EXCEL : str
        Excel database
    SPARQL : str
        SparQL database
    PARQUET : str
        Parquet database
    """

    CSV = "csv"
    SQL = "sql"
    EXCEL = "excel"
    SPARQL = "sparql"
    PARQUET = "parquet"


def load_data(
    database_uri: str, db_type: str = None, query: str = None, sheet_name: str = None
) -> pd.DataFrame:
    """
    Read data from database and give it back to the algorithm.

    If the database type is unknown, this function will exit. Also, a 'query'
    is required for SQL and SparQL databases. If it is not present, this function will
    exit the algorithm.

    Parameters
    ----------
    database_uri : str
        Path to the database file or URI of the database.
    db_type : str
        The type of the database. This should be one of the CSV, SQL,
        Excel, Sparql or Parquet.
    query : str
        The query to execute on the database. This is required for SQL and Sparql
        databases.
    sheet_name : str
        The sheet name to read from the Excel file. This is optional and
        only for Excel databases.

    Returns
    -------
    pd.DataFrame
        The data from the database
    """
    # load initial dataframe
    df = pd.DataFrame()

    loader = _select_loader(db_type)
    if not loader:
        error(
            f"Unknown database type '{db_type}' for database {database_uri}."
            " Please check the node configuration."
        )
        info(f"Available database types: {', '.join(DatabaseType)}")
        exit(1)

    if db_type == DatabaseType.EXCEL:
        df = loader(database_uri, sheet_name=sheet_name)
    elif db_type in (DatabaseType.SQL, DatabaseType.SPARQL):
        if not query:
            error(f"Query is required for database type '{db_type}'")
            exit(1)
        df = loader(database_uri, query=query)
    else:
        df = loader(database_uri)

    return df


def _select_loader(database_type: str) -> callable | None:
    """
    Select the correct wrapper based on the database type.

    Parameters
    ----------
    database_type : str
        The database type to select the wrapper for.

    Returns
    -------
    callable | None
        The wrapper for the specified database type. None if the database type
        is not supported by a wrapper.
    """
    if database_type == "csv":
        return load_csv_data
    elif database_type == "excel":
        return load_excel_data
    elif database_type == "sparql":
        return load_sparql_data
    elif database_type == "parquet":
        return load_parquet_data
    elif database_type == "sql":
        return load_sql_data
    else:
        return None


def load_csv_data(database_uri: str) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the csv file, supplied by te node

    Returns
    -------
    pd.DataFrame
        The data from the csv file
    """
    return pd.read_csv(database_uri)


def load_excel_data(database_uri: str, sheet_name: str = None) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the excel file, supplied by te node
    sheet_name : str | None
        Sheet name to be read from the excel file. If None, the first sheet
        will be read.

    Returns
    -------
    pd.DataFrame
        The data from the excel file
    """
    if sheet_name:
        info(f"Reading sheet '{sheet_name}' from excel file")
    else:
        # The default sheet_name is 0, which is the first sheet
        sheet_name = 0
    # TODO add try/except to check if sheet_name exists
    return pd.read_excel(database_uri, sheet_name=sheet_name)


def load_sparql_data(database_uri: str, query: str) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the triplestore, supplied by te node
    query: str
        Query to retrieve the data from the triplestore

    Returns
    -------
    pd.DataFrame
        The data from the triplestore
    """
    sparql = SPARQLWrapper(database_uri, returnFormat=_SPARQL_RETURN_FORMAT)
    sparql.setQuery(query)

    result = sparql.query().convert().decode()

    return pd.read_csv(io.StringIO(result))


def load_parquet_data(database_uri: str) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the parquet file, supplied by te node

    Returns
    -------
    pd.DataFrame
        The data from the parquet file
    """
    return pd.read_parquet(database_uri)


def _sqldb_uri_preprocess(database_uri: str) -> str:
    """
    Transforms the URI of a file-based/embedded RDBMS on a fully-qualified one, when this URI
    follows the convention /<file system path>/<dbname>.<supported db type>.
    When these conditions are not met, the original URI is returned.

    Pre-condition:
    - the database_uri, if a file-based-one, should exist (this is already validated when the node boots up)

    Parameters:
    - database_path (str): The path to the database file.

    Returns:
    - str: A fully-qualified URI compatible with the database type or the original string if no match found.
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
                # Format the SQLalchemy URI using the database_path and the corresponding URI format
                return uri_format.format(database_uri)
        # Return the original string if no matching extension found
        return database_uri
    else:
        # Return the original string if the URI is not an absolute unix file path
        return database_uri


def load_sql_data(database_uri: str, query: str) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the sql database, supplied by the node
    query: str
        Query to retrieve the data from the database

    Returns
    -------
    pd.DataFrame
        The data from the database
    """
    engine = create_engine(_sqldb_uri_preprocess(database_uri))

    dbapi_conn = engine.raw_connection()

    try:
        # Execute the query and store the results in a DataFrame
        df = pd.read_sql_query(query, con=dbapi_conn)

    finally:
        dbapi_conn.close()  # Ensure the connection is closed

    return df
