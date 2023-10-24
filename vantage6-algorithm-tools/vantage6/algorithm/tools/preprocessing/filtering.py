"""
This module provides a set of utility functions to perform operations on
pandas DataFrames, such as selecting and filtering rows and columns.

Functions
---------
- **select_rows(df, query)**
    Selects rows from a DataFrame based on a query expression. Utilizes
    pandas.DataFrame.query to execute the query.
- **filter_range(df, column, min_, max_, include_min, include_max)**
    Filters the DataFrame rows based on minimum and maximum values for a
    specific column. Inclusion of minimum and maximum values is optional.
- **select_columns(df, columns)**
    Returns a DataFrame containing only the specified columns.
- **select_columns_by_index(df, columns)**
    Similar to select_columns, but columns are specified by their indices or
    slice-strings.
- **drop_columns(df, columns)**
    Returns a DataFrame with the specified columns removed.
- **drop_columns_by_index(df, columns)**
    Similar to drop_columns, but columns are specified by their indices or
    slice-strings.
"""

from typing import List, Optional, Union

import pandas as pd


def _extract_columns(
    df: pd.DataFrame, columns: List[Union[int, str]]
) -> List[str]:
    """
    Extract column names from the DataFrame based on indices or slice-strings.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame from which to extract columns.
    columns : list
        A list of indices or slice-strings specifying the columns to extract.

    Returns
    -------
    list
        A list of column names corresponding to the specified indices or
        slice-strings.
    """
    extracted_cols = []
    for col in columns:
        if isinstance(col, int):
            extracted_cols.append(df.columns[col])
        elif isinstance(col, str) and ":" in col:
            start, end = col.split(":")
            start = int(start) if start else None
            end = int(end) if end else None
            extracted_cols.extend(df.columns[start:end])
        else:
            raise ValueError(
                f"Column specifier {col} is not an integer or slice-string "
                f"(e.g. '1:3')."
            )

    return extracted_cols


def select_rows(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Select rows from the data based on a query. It uses the
    pandas.DataFrame.query function to filter the data. See the documentation
    of that function for more information on the query syntax.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    query : str
        The query to filter on.

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

    for more examples, see the documentation of pandas.DataFrame.query
    """
    return df.query(query)


def filter_range(
    df: pd.DataFrame,
    column: str,
    min_: float = None,
    max_: float = None,
    include_min: bool = True,
    include_max: bool = True,
) -> pd.DataFrame:
    """
    Filter the data based on a minimum and/or maximum value.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    column : str
        The column to filter on.
    min_ : float, optional
        The minimum value to filter on, by default None.
    max_ : float, optional
        The maximum value to filter on, by default None.
    include_min : bool, optional
        Whether to include the minimum value, by default True.
    include_max : bool, optional
        Whether to include the maximum value, by default True.

    Returns
    -------
    pandas.DataFrame
        The filtered data.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({'A': [1, 2, 3, 4, 5]})
    >>> filter_range(df, 'A', min_=2, max_=4)
       A
    1  2
    2  3
    3  4
    >>> filter_range(df, 'A', min_=2)
       A
    1  2
    2  3
    3  4
    4  5
    >>> filter_range(df, 'A', max_=4)
       A
    0  1
    1  2
    2  3
    3  4
    >>> df = pd.DataFrame({'A': [1.0, 2.1, 2.9, 3.5, 4.0]})
    >>> filter_range(df, 'A', max_=4.0, include_max=False)
         A
    0  1.0
    1  2.1
    2  2.9
    3  3.5
    """
    if column is None:
        column = df.index.name

    if min_ is not None:
        if include_min:
            df = df[df[column] >= min_]
        else:
            df = df[df[column] > min_]

    if max_ is not None:
        if include_max:
            df = df[df[column] <= max_]
        else:
            df = df[df[column] < max_]

    return df


def select_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Select columns from the data.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    columns : list
        A list of names of the columns to keep in the provided order.

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


def select_columns_by_index(
    df: pd.DataFrame, columns: List[Union[int, str]]
) -> pd.DataFrame:
    """
    Select columns from the data.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    columns : list
        A list of indices or slice-strings of the columns to keep in the
        provided order.


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

    >>> select_columns_by_index(df, [0, 2])
       a   c
    0  1  11
    1  2  12
    2  3  13
    3  4  14
    4  5  15

    >>> select_columns_by_index(df, [2, 0])
        c  a
    0  11  1
    1  12  2
    2  13  3
    3  14  4
    4  15  5

    slice examples:
    >>> df = pd.DataFrame(
    ...     {
    ...         "a": [1, 2],
    ...         "b": [3, 4],
    ...         "c": [5, 6],
    ...         "d": [7, 8],
    ...         "e": [9, 10]
    ...     }
    ... )

    >>> select_columns_by_index(df, [0, 2])
       a  c
    0  1  5
    1  2  6

    >>> select_columns_by_index(df, ['0:3'])
       a  b  c
    0  1  3  5
    1  2  4  6

    >>> select_columns_by_index(df, [0, '1:4', 4])
       a  b  c  d   e
    0  1  3  5  7   9
    1  2  4  6  8  10

    """
    return df[_extract_columns(df, columns)]


def drop_columns(df: pd.DataFrame, columns: list) -> pd.DataFrame:
    """
    Drop columns from the data.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    columns : list
        A list of names of the columns to drop.

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


def drop_columns_by_index(
    df: pd.DataFrame, columns: List[Union[int, str]]
) -> pd.DataFrame:
    """
    Drop columns from the data.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to filter.
    columns : list
        A list of indices or slice-strings of the columns to drop.

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
    >>> drop_columns_by_index(df, [0, 2])
        b
    0   6
    1   7
    2   8
    3   9
    4  10

    >>> drop_columns_by_index(df, [-1])
       a   b
    0  1   6
    1  2   7
    2  3   8
    3  4   9
    4  5  10

    >>> df = pd.DataFrame(
    ...     {
    ...         "a": [1, 2],
    ...         "b": [3, 4],
    ...         "c": [5, 6],
    ...         "d": [7, 8],
    ...         "e": [9, 10]
    ...     }
    ... )

    >>> drop_columns_by_index(df, [0, 2])
       b  d   e
    0  3  7   9
    1  4  8  10

    >>> drop_columns_by_index(df, ['0:3'])
       d   e
    0  7   9
    1  8  10

    >>> drop_columns_by_index(df, ['1:4', 4])
       a
    0  1
    1  2

    """

    return df.drop(_extract_columns(df, columns), axis=1)


def filter_by_date(
    df: pd.DataFrame,
    column: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keep_between: bool = True,
    fmt: Optional[str] = None,
) -> pd.DataFrame:
    """
    Filters a DataFrame based on a datetime column within a given start and end
    date.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    column : str
        The column containing datetime information.
    start_date : Optional[str]
        The start date for filtering. Format should follow `fmt`.
    end_date : Optional[str]
        The end date for filtering. Format should follow `fmt`.
    keep_between : bool, default=True
        If True, keep rows between start and end date. If False, keep rows
        outside the interval.
    fmt : Optional[str]
        The datetime format to use for parsing dates.

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
        raise ValueError(
            "At least one of start_date or end_date must be provided."
        )

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
