from typing import Callable

import pandas as pd

from vantage6.common import error, info
from vantage6.common.enum import StrEnumBase

from vantage6.algorithm.data_extraction import (
    _read_csv,
    _read_excel,
    _read_parquet,
    _read_sparql_database,
    _read_sql_database,
)


class MockDatabaseType(StrEnumBase):
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


def load_mock_data(
    database_uri: str,
    database_type: str | None = None,
    query: str | None = None,
    sheet_name: str | None = None,
) -> pd.DataFrame:
    """
    Load data from a mock client

    Parameters
    ----------
    database_uri : str
        The URI of the database to load data from.
    database_type : str, optional
        The type of the database to load data from.
    query : str, optional
        The query to execute on the database.
    sheet_name : str, optional
        The name of the sheet to load data from.

    Returns
    -------
    pd.DataFrame
        The data from the database.
    """
    loader = _select_loader(database_type)
    if not loader:
        error(
            f"Unknown database type '{database_type}' for database {database_uri}."
            " Please check the node configuration."
        )
        info(f"Available mock database types: {', '.join(MockDatabaseType.list())}")
        exit(1)

    connection_details = {
        "uri": database_uri,
        "type": database_type,
    }
    if database_type == MockDatabaseType.EXCEL:
        return loader(connection_details, sheet_name=sheet_name)
    elif (
        database_type == MockDatabaseType.SPARQL
        or database_type == MockDatabaseType.SQL
    ):
        if not query:
            error(f"Query is required for {database_type} databases.")
            exit(1)
        return loader(connection_details, query)
    else:
        return loader(connection_details)


def _select_loader(database_type: str) -> Callable | None:
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
        return _read_csv
    elif database_type == "excel":
        return _read_excel
    elif database_type == "sparql":
        return _read_sparql_database
    elif database_type == "parquet":
        return _read_parquet
    elif database_type == "sql":
        return _read_sql_database
    else:
        return None
