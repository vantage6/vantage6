"""
This module contains several preprocessing functions that may be used to
prepare the data for the algorithm.
"""

import pandas as pd


def select_rows(df: pd.DataFrame, query: str) -> pd.DataFrame:
    """
    Select rows from the data based on a query. It uses the pandas.DataFrame.query
    function to filter the data. See the documentation of that function for more
    information on the query syntax.

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
    include_min: bool = False,
    include_max: bool = False,
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
        Whether to include the minimum value, by default False.
    include_max : bool, optional
        Whether to include the maximum value, by default False.

    Returns
    -------
    pandas.DataFrame
        The filtered data.
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


# TODO delete later on
def dummy_preprocess(df: pd.DataFrame) -> pd.DataFrame:
    """
    Dummy preprocessing function that does nothing.

    Parameters
    ----------
    df : pandas.DataFrame
        The data to preprocess.

    Returns
    -------
    pandas.DataFrame
        The preprocessed data.
    """
    return df
