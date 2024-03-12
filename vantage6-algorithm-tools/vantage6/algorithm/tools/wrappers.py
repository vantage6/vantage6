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
import pandas as pd
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


def get_column_names(
    database_uri: str, db_type: str = None, query: str = None, sheet_name: str = None
) -> list[str]:
    """
    Get the column names of dataframe that will be loaded into an algorithm

    Parameters
    ----------
    database_uri : str
        Path to the database file or URI of the database.
    db_type : str
        The type of the database. This should be one of the CSV, SQL, Excel, Sparql or
        Parquet.
    query : str
        The query to execute on the database. This is required for SQL and Sparql
        databases.
    sheet_name : str
        The sheet name to read from the Excel file. This is optional and only for Excel
        databases.

    Returns
    -------
    list[str]
        The column names of the dataframe
    """
    df = load_data(database_uri, db_type, query, sheet_name)
    return df.columns.tolist()


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


def load_sql_data(database_uri: str, query: str) -> pd.DataFrame:
    """
    Load the local privacy-sensitive data from the database.

    Parameters
    ----------
    database_uri : str
        URI of the sql database, supplied by te node
    query: str
        Query to retrieve the data from the database

    Returns
    -------
    pd.DataFrame
        The data from the database
    """
    return pd.read_sql(database_uri, query)
