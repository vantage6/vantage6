"""
This module provides a set of utility functions to perform operations on
pandas DataFrames, such as selecting and filtering rows and columns.
"""

import pandas as pd

from vantage6.algorithm.tools.error_handling import handle_data_errors
from vantage6.algorithm.tools.exceptions import UserInputError

from vantage6.algorithm.decorator.action import preprocessing
from vantage6.algorithm.preprocessing.expression import evaluate_expression


@handle_data_errors
@preprocessing
def select_rows(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Select the rows of the data for which the query is true.

    Parameters
    ----------
    df : pd.DataFrame
        The data to filter.
    query : str
        The condition that rows must meet, e.g. ``age >= 18 and sex == 'F'``.
        Supported are column names, numbers, strings, ``True``, ``False``, ``None``,
        the operators ``+ - * / // %`` (only ``+`` for text), comparisons
        (``== != < <= > >=``), ``in``/``not in`` a list of constants,
        ``and or not & | ~`` and the functions
        ``abs, sqrt, log, log2, log10, exp, floor, ceil, round``. Other functions,
        attribute access, indexing and ``**`` are not supported. The query may be at
        most 250 characters long.

    Returns
    -------
    pandas.DataFrame
        The filtered data.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame(
    ...     {
    ...         "a": [1, 2, 3, 4, 5],
    ...         "b": [6, 7, 8, 9, 10],
    ...         "c": [11, 12, 13, 14, 15],
    ...     }
    ... )
    >>> df
       a   b   c
    0  1   6  11
    1  2   7  12
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> select_rows(df, "a > 2")
       a   b   c
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> select_rows(df, "a > 2 and b < 10")
       a  b   c
    2  3  8  13
    3  4  9  14

    >>> select_rows(df, "a > 2 or c < 12")
       a   b   c
    0  1   6  11
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> select_rows(df, "2 * a + b > c")
       a   b   c
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> select_rows(df, "a in [1, 5]")
       a   b   c
    0  1   6  11
    4  5  10  15
    """
    mask = evaluate_expression(df, query)
    if not isinstance(mask, pd.Series) or not pd.api.types.is_bool_dtype(mask):
        raise UserInputError("The query must evaluate to true or false for each row.")
    return df[mask]


@handle_data_errors
@preprocessing
def filter_range(
    df: pd.DataFrame,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
    include_min: bool = True,
    include_max: bool = True,
) -> pd.DataFrame:
    """
    Filter the data based on a minimum and/or maximum value in a given column.

    Parameters
    ----------
    df : pd.DataFrame
        The data to filter.
    column : str, optional
        The column to filter on.
    min_value : float, optional
        The minimum value to filter on, by default None. If None, no lower
        bound is applied.
    max_value : float, optional
        The maximum value to filter on, by default None. If None, no upper
        bound is applied.
    include_min : bool, optional
        Whether to include rows where the column value is equal to min_value,
        by default True.
    include_max : bool, optional
        Whether to include rows where the column value is equal to max_value,
        by default True.

            Returns
    -------
    pandas.DataFrame
        The filtered data.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 5]})
    >>> filter_range(df, 'A', min_value=2, max_value=4)
       A
    1  2
    2  3
    3  4
    >>> filter_range(df, 'A', min_value=2)
       A
    1  2
    2  3
    3  4
    4  5
    >>> filter_range(df, 'A', max_value=4)
       A
    0  1
    1  2
    2  3
    3  4
    >>> df = pd.DataFrame({'A': [1.0, 2.1, 2.9, 3.5, 4.0]})
    >>> filter_range(df, 'A', max_value=4.0, include_max=False)
         A
    0  1.0
    1  2.1
    2  2.9
    3  3.5
    """
    if column is None:
        column = df.index.name

    if min_value is not None:
        if include_min:
            df = df[df[column] >= min_value]
        else:
            df = df[df[column] > min_value]

    if max_value is not None:
        if include_max:
            df = df[df[column] <= max_value]
        else:
            df = df[df[column] < max_value]

    return df


@handle_data_errors
@preprocessing
def select_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Select specific columns from a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame from which to select columns.
    columns : list
        A list of column names to keep in the resulting DataFrame.

    Returns
    -------
    pandas.DataFrame
        The filtered data.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame(
    ...     {
    ...         "a": [1, 2, 3, 4, 5],
    ...         "b": [6, 7, 8, 9, 10],
    ...         "c": [11, 12, 13, 14, 15],
    ...     }
    ... )
    >>> df
       a   b   c
    0  1   6  11
    1  2   7  12
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> select_columns(df, ["a", "c"])
       a   c
    0  1  11
    1  2  12
    2  3  13
    3  4  14
    4  5  15

    >>> select_columns(df, ["c", "a"])
        c  a
    0  11  1
    1  12  2
    2  13  3
    3  14  4
    4  15  5

    """
    return df[columns]


@handle_data_errors
@preprocessing
def drop_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Drop specified columns from the DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame from which columns will be dropped.
    columns : list
        A list of column names to be dropped from the DataFrame.

    Returns
    -------
    pandas.DataFrame
        The filtered data.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame(
    ...     {
    ...         "a": [1, 2, 3, 4, 5],
    ...         "b": [6, 7, 8, 9, 10],
    ...         "c": [11, 12, 13, 14, 15],
    ...     }
    ... )
    >>> df
       a   b   c
    0  1   6  11
    1  2   7  12
    2  3   8  13
    3  4   9  14
    4  5  10  15

    >>> drop_columns(df, ["a", "c"])
        b
    0   6
    1   7
    2   8
    3   9
    4  10

    """
    return df.drop(columns, axis=1)


@handle_data_errors
@preprocessing
def filter_by_date(
    df: pd.DataFrame,
    column: str,
    start_date: str | None = None,
    end_date: str | None = None,
    keep_between: bool = True,
    fmt: str | None = None,
) -> pd.DataFrame:
    """
    Filters a DataFrame based on a datetime column within a given start and end
    date.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame to be filtered.
    column : str
        The name of the column containing datetime information.
    start_date : str, default=None
        The starting date of the period for filtering. Rows with dates on or
        after this date are included.
    end_date : str, default=None
        The ending date of the period for filtering. Rows with dates on or
        before this date are included.
    keep_between : bool, default=True
        Determines if rows within the date range (inclusive) should be kept; if
        False, rows outside the range are kept.
    fmt : str, default=None
        The format string for parsing the dates in the datetime column if they
        are stored as strings.

    Returns
    -------
    pd.DataFrame
        The filtered DataFrame.

    Example
    -------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'date': ['2021-01-01', '2021-01-02', '2021-01-03', '2021-01-04'],
    ...     'value': [1, 2, 3, 4]
    ... })
    >>> filter_by_date(df, 'date', start_date='2021-01-02',
    ... end_date='2021-01-03')
             date  value
    1  2021-01-02      2
    2  2021-01-03      3
    >>> filter_by_date(df, 'date', start_date='2021-01-02',
    ... end_date='2021-01-03', keep_between=False)
             date  value
    0  2021-01-01      1
    3  2021-01-04      4
    """
    if start_date is None and end_date is None:
        raise ValueError("At least one of start_date or end_date must be provided.")

    # Convert the column to datetime type
    datetimes = pd.to_datetime(df[column], format=fmt)

    if start_date:
        start_date = pd.Timestamp(start_date)

    if end_date:
        end_date = pd.Timestamp(end_date)

    if keep_between:
        if start_date and end_date:
            mask = (datetimes >= start_date) & (datetimes <= end_date)
        elif start_date:
            mask = datetimes >= start_date
        else:
            mask = datetimes <= end_date
    else:
        if start_date and end_date:
            mask = (datetimes < start_date) | (datetimes > end_date)
        elif start_date:
            mask = datetimes < start_date
        else:
            mask = datetimes > end_date

    return df[mask]
