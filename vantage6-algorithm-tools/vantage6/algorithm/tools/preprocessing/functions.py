"""
This module contains several preprocessing functions that may be used to
prepare the data for the algorithm.
"""

from datetime import date
from typing import Dict, List, Optional, Union

import pandas as pd
import numpy as np


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
    pandas.DataFrame.query function to filter the data. See the documentation of
    that function for more information on the query syntax.

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


def rename_columns(
    df: pd.DataFrame, new_names: Union[Dict[str, str], List[str]]
) -> pd.DataFrame:
    """
    Rename DataFrame columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame whose columns you want to rename.
    new_names : dict or list
        If a dict, a mapping from current column names to new names.
        If a list, new column names in order; the length should match the number of columns.

    Returns
    -------
    pandas.DataFrame
        DataFrame with renamed columns.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'a': [1, 2],
    ...     'b': [3, 4]
    ... })
    >>> rename_columns(df, {'a': 'x', 'b': 'y'})
       x  y
    0  1  3
    1  2  4

    >>> rename_columns(df, ['x', 'y'])
       x  y
    0  1  3
    1  2  4
    """

    if isinstance(new_names, dict):
        return df.rename(columns=new_names)
    elif isinstance(new_names, list):
        if len(new_names) != len(df.columns):
            raise ValueError(
                "Length of new names list must match the number of columns"
            )
        return df.set_axis(new_names, axis=1, copy=True)
    else:
        raise TypeError("Invalid type for new_names; expected a dict or list")


def min_max_scale(
    df: pd.DataFrame,
    min_vals: List[float],
    max_vals: List[float],
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Perform min-max scaling on specified columns of a DataFrame using the
    formula (x - min) / (max - min). The function is applied in a federated
    setting, meaning one node does not know the global min and mix. This means
    the minimum and maximum values for each column must be specified.
    If columns are not provied, all columns are scaled and the length of
    min_vals and max_vals must match the number of DataFrame columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to scale.
    min_vals : list
        List of minimum values for scaling; should match the length of columns.
    max_vals : list
        List of maximum values for scaling; should match the length of columns.
    columns : list, optional
        List of columns to scale; if None, all columns are scaled and length of min_vals and max_vals must match df.columns.

    Returns
    -------
    pandas.DataFrame
        DataFrame with scaled columns.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'a': [1, 2, 3],
    ...     'b': [4, 5, 6]
    ... })
    >>> min_max_scale(df, [0, 1], [2, 3], ['a', 'b'])
         a    b
    0  0.5  1.5
    1  1.0  2.0
    2  1.5  2.5

    >>> min_max_scale(df, [1, 4], [3, 6])
         a    b
    0  0.0  0.0
    1  0.5  0.5
    2  1.0  1.0
    """

    if columns is None:
        if len(min_vals) != len(max_vals) or len(min_vals) != len(df.columns):
            raise ValueError(
                "Length of min_vals and max_vals must match the number of "
                "DataFrame columns when columns is None"
            )
        columns = df.columns.tolist()
    else:
        if len(min_vals) != len(max_vals) or len(min_vals) != len(columns):
            raise ValueError(
                "Length of min_vals and max_vals must match the number of "
                "specified columns"
            )

    df_scaled = df.copy()
    for col, min_val, max_val in zip(columns, min_vals, max_vals):
        df_scaled[col] = (df[col] - min_val) / (max_val - min_val)

    return df_scaled


def standard_scale(
    df: pd.DataFrame,
    means: List[float],
    stds: List[float],
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Perform standard scaling on specified columns of a DataFrame using the
    formula (x - mean) / std. The function is applied in a federated
    setting, meaning one node does not know the global mean and std. This means
    the mean and standard deviation values for each column must be specified.
    If columns are not provided, all columns are scaled and the length of
    means and stds must match the number of DataFrame columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to scale.
    means : list
        List of mean values for scaling; should match the length of columns.
    stds : list
        List of standard deviation values for scaling; should match the length of columns.
    columns : list, optional
        List of columns to scale; if None, all columns are scaled and the length of means and stds must match df.columns.

    Returns
    -------
    pandas.DataFrame
        DataFrame with scaled columns.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'a': [1, 2, 3],
    ...     'b': [4, 5, 6]
    ... })
    >>> standard_scale(df, [1, 4], [1, 1], ['a', 'b'])
         a    b
    0  0.0  0.0
    1  1.0  1.0
    2  2.0  2.0

    >>> standard_scale(df, [2, 5], [1, 1])
         a    b
    0 -1.0 -1.0
    1  0.0  0.0
    2  1.0  1.0
    """

    if columns is None:
        if len(means) != len(stds) or len(means) != len(df.columns):
            raise ValueError(
                "Length of means and stds must match the number of DataFrame columns when columns is None"
            )
        columns = df.columns.tolist()
    else:
        if len(means) != len(stds) or len(means) != len(columns):
            raise ValueError(
                "Length of means and stds must match the number of specified columns"
            )

    df_scaled = df.copy()
    for col, mean, std in zip(columns, means, stds):
        df_scaled[col] = (df[col] - mean) / std

    return df_scaled


def one_hot_encode(
    df: pd.DataFrame,
    column: str,
    categories: List[str],
    unknown_category: Optional[str] = "unknown",
    drop_original: bool = True,
    prefix: Optional[str] = None,
) -> pd.DataFrame:
    """
    Perform one-hot encoding on a specific column of a DataFrame. As one node
    may not have access to all possible categories in the entire dataset. This
    requires predefined categories to be specified upfront. The function allows
    encoding of unseen categories into a specified 'unknown' category label.
    The original column can be optionally dropped, and a prefix can be added
    to the new one-hot encoded columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to encode.
    column : str
        The column to one-hot encode.
    categories : list
        List of predefined categories.
    unknown_category : str, optional
        Label for unseen categories.
    drop_original : bool, optional
        Whether to drop the original column, default is True.
    prefix : str, optional
        Prefix for the new one-hot encoded columns.

    Returns
    -------
    pandas.DataFrame
        DataFrame with one-hot encoded column.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'color': ['red', 'green', 'blue', 'yellow']
    ... })

    >>> one_hot_encode(df, 'color', ['red', 'green', 'blue'])
       blue  green  red  unknown
    0     0      0    1        0
    1     0      1    0        0
    2     1      0    0        0
    3     0      0    0        1

    >>> one_hot_encode(df, 'color', ['red', 'green'], drop_original=False)
        color  green  red  unknown
    0     red      0    1        0
    1   green      1    0        0
    2    blue      0    0        1
    3  yellow      0    0        1

    >>> one_hot_encode(df, 'color', ['red', 'green'], unknown_category='other', prefix='col')
       col_green  col_other  col_red
    0          0          0        1
    1          1          0        0
    2          0          1        0
    3          0          1        0

    """

    # Map unseen categories to the unknown_category label
    df_copy = df.copy()
    df_copy[column] = df_copy[column].apply(
        lambda x: x if x in categories else unknown_category
    )

    # Perform one-hot encoding
    one_hot_df = pd.get_dummies(df_copy[column], prefix=prefix)

    # Merge one-hot encoded DataFrame with the original DataFrame
    df_out = pd.concat([df, one_hot_df], axis=1)

    # Drop the original column if specified
    if drop_original:
        df_out.drop(column, axis=1, inplace=True)

    return df_out


def encode(
    df: pd.DataFrame,
    columns: list,
    mapping: Dict,
    unknown_value: Union[str, int] = -1,
    raise_on_unknown: bool = False,
) -> pd.DataFrame:
    """
    Custom encoding of DataFrame columns using a provided mapping.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to encode.
    columns : list
        List of column names to be encoded.
    mapping : Dict
        Dictionary containing the mapping for encoding. Keys are original values
        and values are the new encoded values.
    unknown_value : Union[str, int]
        Value to use for any unknown categories.
    raise_on_unknown : bool
        If True, raises an error when encountering an unknown category.
        Otherwise, uses `unknown_value`.

    Returns
    -------
    pandas.DataFrame
        The encoded DataFrame.

    Examples
    --------
    >>> df = pd.DataFrame({
    ...     'color': ['red', 'green', 'purple'],
    ...     'shape': ['circle', 'square', 'pentagon']
    ... })

    >>> mapping = {'red': 1, 'green': 2, 'circle': 'A', 'square': 'B'}
    >>> encode(df, ['color', 'shape'], mapping)
       color shape
    0      1     A
    1      2     B
    2     -1    -1

    >>> encode(df, ['color', 'shape'], mapping, unknown_value='N/A')
      color shape
    0     1     A
    1     2     B
    2   N/A   N/A

    >>> encode(df, ['color'], mapping, unknown_value=3)
       color     shape
    0      1    circle
    1      2    square
    2      3  pentagon

    """

    encoded_df = df.copy()
    for col in columns:
        unique_vals = set(encoded_df[col].unique()) - set(mapping.keys())
        if raise_on_unknown and unique_vals:
            raise ValueError(
                f"Unknown categories {unique_vals} encountered in column {col}."
            )
        encoded_df[col] = encoded_df[col].apply(
            lambda x: mapping.get(x, unknown_value)
        )

    return encoded_df


def assign_column(
    df: pd.DataFrame, column_name: str, expression: str, overwrite: bool = False
) -> pd.DataFrame:
    """
    Create or modify a column in a new DataFrame based on the given expression.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame from which a new DataFrame will be created.
    column_name : str
        The name of the new or existing column.
    expression : str
        The expression used to create or modify the column. The expression can
        be any valid pandas DataFrame eval() expression, which includes
        arithmetic, comparison, and logical  operations. For more details, see:
        https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.eval.html
    overwrite : bool, optional
        Whether to overwrite the column if it already exists in the new
        DataFrame (default is False).

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with the new or modified column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]})
    >>> new_df = assign_column(df, "C", "A + B")
    >>> new_df
       A  B  C
    0  1  4  5
    1  2  5  7
    2  3  6  9

    >>> another_df = assign_column(new_df, "B", "A * B", overwrite=True)
    >>> another_df
       A   B  C
    0  1   4  5
    1  2  10  7
    2  3  18  9
    """

    new_df = df.copy()
    if column_name in new_df.columns and not overwrite:
        raise ValueError(
            f"Column '{column_name}' already exists and overwrite is set to"
            "False."
        )

    new_df[column_name] = new_df.eval(expression)
    return new_df


def discretize_column(
    df: pd.DataFrame,
    column_name: str,
    bins: Union[int, List[Union[int, float]]],
    labels: List[str] = None,
    right: bool = True,
    include_lowest: bool = False,
    output_column_name: str = None,
) -> pd.DataFrame:
    """
    Discretize a column in a new DataFrame based on the given bin edges or
    number of bins.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame from which a new DataFrame will be created.
    column_name : str
        The name of the column to discretize.
    bins : int or list of int or float
        The number of bins to create or the specific bin edges.
    labels : list of str, optional
        Labels to assign to the bins.
    right : bool, optional
        Indicates whether bins include the rightmost edge or not (default is
        True).
    include_lowest : bool, optional
        Whether the first interval should include the lowest value or not
        (default is False).
    output_column_name : str, optional
        The name of the output column that contains the discretized data.
        If not specified, the original column will be replaced.

    Returns
    -------
    pandas.DataFrame
        A new DataFrame with the discretized column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"Age": [25, 35, 45, 55]})
    >>> discretize_column(df, "Age", [20, 30, 40, 50, 60])
            Age
    0  (20, 30]
    1  (30, 40]
    2  (40, 50]
    3  (50, 60]

    >>> discretize_column(df, "Age", [20, 30, 40, 50, 60], labels=["Young",
    ... "Middle", "Senior", "Old"], output_column_name="AgeCategory")
       Age AgeCategory
    0   25       Young
    1   35      Middle
    2   45      Senior
    3   55         Old
    """

    new_df = df.copy()
    new_column = pd.cut(
        df[column_name],
        bins=bins,
        labels=labels,
        right=right,
        include_lowest=include_lowest,
    )

    if output_column_name is None:
        output_column_name = column_name

    new_df[output_column_name] = new_column
    return new_df


def to_datetime(
    df: pd.DataFrame,
    column: Optional[str] = None,
    fmt: Optional[str] = None,
    errors: str = "raise",
    input_value: Optional[str] = None,
    output_column: Optional[str] = None,
) -> pd.DataFrame:
    """
    Convert a string column or a string input to a datetime column in a new
    DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str or None, default None
        The name of the column to convert. If None, `input_value` must be
        provided.
    fmt : str, optional
        String to use as date format. See the following link for more
        information: https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior
    errors : str, default 'raise'
        Errors handling if a string cannot be converted:
        * If 'raise', then invalid parsing will raise an exception.
        * If 'coerce', then invalid parsing will be set as NaT.
        * If 'ignore', then invalid parsing will return the input.
    input_value : str, optional
        String input to be converted to datetime if `column` is None.
    output_column : str, optional
        Output column name when `input_value` is used.

    Returns
    -------
    pd.DataFrame
        DataFrame with the converted column.

    Examples
    --------
    # Converting an existing column
    >>> df = pd.DataFrame({"date_str": ["2021-01-01", "2021-02-01",
    ... "2021-03-01"]})
    >>> to_datetime(df, "date_str")
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    # Adding a new column with a fixed date
    >>> to_datetime(df, input_value="2021-04-01", output_column="new_date")
         date_str   new_date
    0  2021-01-01 2021-04-01
    1  2021-02-01 2021-04-01
    2  2021-03-01 2021-04-01

    >>> import pandas as pd
    >>> df = pd.DataFrame({"date_str": ["2021-01-01", "2021-02-01",
    ... "2021-03-01"]})
    >>> to_datetime(df, "date_str")
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> to_datetime(df, "date_str", fmt='%Y-%m-%d')
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> df = pd.DataFrame({"date_str": ["01-2021-01", "01-2021-02",
    ... "01-2021-03"]})
    >>> to_datetime(df, "date_str", fmt='%d-%Y-%m')
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> df = pd.DataFrame({"date_str": ["Jan 01, 2021", "Feb 01, 2021",
    ... "Mar 01, 2021"]})
    >>> to_datetime(df, "date_str", fmt='%b %d, %Y')
        date_str
    0 2021-01-01
    1 2021-02-01
    2 2021-03-01

    >>> df = pd.DataFrame({"date_str": ["01-2021-01", "01-2021-02", "Invalid"]})
    >>> to_datetime(df, "date_str", fmt='%d-%Y-%m', errors='coerce')
        date_str
    0 2021-01-01
    1 2021-02-01
    2        NaT
    """

    new_df = df.copy()

    if column is None:
        if input_value is None or output_column is None:
            raise ValueError(
                "If `column` is None, both `input_value` and `output_column` must be provided."
            )
        new_df[output_column] = pd.to_datetime(
            input_value, format=fmt, errors=errors
        )
    else:
        new_df[column] = pd.to_datetime(
            new_df[column], format=fmt, errors=errors
        )

    return new_df


def to_timedelta(
    df: pd.DataFrame,
    input_column: Optional[str] = None,
    duration: Optional[Union[str, int]] = None,
    unit: str = "days",
    output_column: Optional[str] = None,
    errors: str = "raise",
) -> pd.DataFrame:
    """
    Convert a string column or apply a fixed duration to a new timedelta column
    in a new DataFrame.

    For more information see: https://pandas.pydata.org/docs/reference/api/pandas.Timedelta.html

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    input_column : str, optional
        The name of the column to convert.
    duration : str or int, optional
        A fixed duration to apply to all rows. Could be either a string like
        '1 days' or an integer.
    unit : str, default 'days'
        The unit for the fixed duration, applicable when `duration` is an
        integer.

        Possible values:
        * W, D, T, S, L, U, or N
        * days or day
        * hours, hour, hr, or h

    output_column : str, optional
        The name of the output column. Required if using the `duration`
        parameter.
    errors : str, default 'raise'
        Errors handling if a string cannot be converted:
        * If 'raise', then invalid parsing will raise an exception.
        * If 'coerce', then invalid parsing will be set as NaT.
        * If 'ignore', then invalid parsing will return the input.

    Returns
    -------
    pd.DataFrame
        DataFrame with the new converted or created column, retaining the
        original column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"time_str": ["1 days", "2 days", "3 days"]})
    >>> to_timedelta(df, input_column="time_str", output_column="new_column")
      time_str new_column
    0   1 days     1 days
    1   2 days     2 days
    2   3 days     3 days

    >>> to_timedelta(df, duration=4, unit='W', output_column="fixed_timedelta")
      time_str fixed_timedelta
    0   1 days         28 days
    1   2 days         28 days
    2   3 days         28 days

    >>> to_timedelta(df, duration=48, unit='hours', output_column="duration")
      time_str duration
    0   1 days   2 days
    1   2 days   2 days
    2   3 days   2 days
    """

    new_df = df.copy()

    if input_column is not None:
        if output_column is None:
            raise ValueError(
                "The `output_column` must be specified when using `column`."
            )
        new_df[output_column] = pd.to_timedelta(
            new_df[input_column], errors=errors
        )

    if duration is not None:
        if output_column is None:
            raise ValueError(
                "The `output_column` must be specified when using `duration`."
            )
        if isinstance(duration, int):
            duration = f"{duration} {unit}"
        new_df[output_column] = pd.to_timedelta(duration, errors=errors)

    if input_column is None and duration is None:
        raise ValueError("Either `column` or `duration` must be specified.")

    return new_df


def timedelta(
    df: pd.DataFrame,
    column: str,
    output_column: str,
    reference_date: Optional[pd.Timestamp] = None,
) -> pd.DataFrame:
    """
    Convert a datetime column to a timedelta column in days in a new DataFrame,
    where the result is the number of days since the date in the column to the
    reference date, which defaults to today.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    column : str
        The name of the datetime column to convert to a timedelta.
    output_column : str
        Output column name.
    reference_date : pd.Timestamp, optional
        The date to which the timedelta is calculated. Defaults to today.

    Returns
    -------
    pd.DataFrame
        DataFrame with the timedelta column in days.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"date": [pd.Timestamp("2021-01-01"),
    ... pd.Timestamp("2021-02-01")]})
    >>> timedelta(df, "date", "days_to_jan15",
    ... reference_date=pd.Timestamp("2021-01-15"))
            date  days_to_jan15
    0 2021-01-01             14
    1 2021-02-01            -17

    >>> today = pd.to_datetime("today")
    >>> df = pd.DataFrame({"birthdate": [today - pd.Timedelta(days=300),
    ... today - pd.Timedelta(days=250)]})
    >>> df['birthdate'] = df['birthdate'].dt.date
    >>> df = timedelta(df, "birthdate", "age_in_days")
    >>> df[['age_in_days']]
       age_in_days
    0          300
    1          250

    """

    if reference_date is None:
        reference_date = pd.to_datetime("today")
    else:
        reference_date = pd.Timestamp(reference_date)

    new_df = df.copy()
    duration_col = (reference_date - pd.to_datetime(new_df[column])).dt.days

    new_df[output_column] = duration_col

    return new_df


def calculate_age(
    df: pd.DataFrame,
    birthdate_column: str,
    output_column: str,
    reference_date: Optional[date] = None,
) -> pd.DataFrame:
    """
    Calculate the calendar age in years from the birthdate column to a reference
    date (defaults to today).

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame.
    birthdate_column : str
        The name of the column containing birthdate information.
    output_column : str
        The name of the column to store the age.
    reference_date : date, optional
        The date to use as the reference for calculating age. Defaults to
        today's date.

    Returns
    -------
    pd.DataFrame
        DataFrame with the calculated age column.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"birthdate": [pd.Timestamp("2000-01-01"),
    ... pd.Timestamp("1980-05-15")]})
    >>> df['birthdate'] = df['birthdate'].dt.date
    >>> calculate_age(df, "birthdate", "age", reference_date=date(2025, 1, 1))
        birthdate  age
    0  2000-01-01   25
    1  1980-05-15   44
    """

    new_df = df.copy()

    if reference_date is None:
        reference_date = date.today()

    def compute_age(birthdate):
        return (
            reference_date.year
            - birthdate.year
            - (
                (reference_date.month, reference_date.day)
                < (birthdate.month, birthdate.day)
            )
        )

    new_df[output_column] = new_df[birthdate_column].apply(compute_age)

    return new_df


def collapse(
    df: pd.DataFrame,
    groupby_columns: List[str],
    aggregation: Union[
        str,
        callable,
        Dict[str, Union[str, callable, List[Union[str, callable]]]],
    ],
    strict_mode: bool = True,
) -> pd.DataFrame:
    """
    Collapses a DataFrame by grouping by one or more columns and aggregating the
    rest.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    groupby_columns : List[str]
        Columns by which the DataFrame will be grouped.
    aggregation : Union[str, callable, Dict[str, Union[str, callable, List[Union[str, callable]]]]]
        The aggregation strategy to apply. Can be a string to apply to all columns,
        or a dictionary specifying the aggregation for each column. The strategy
        can also be a list of strategies, which will then provide multiple columns.

        Valid aggregation strategies:
        String:
        * "sum"
        * "mean"
        * "min"
        * "max"
        * "count"
        * "std": Standard Deviation
        * "var": Variance
        * "first": First non-null value in the group
        * "last": Last non-null value in the group
        * "nunique": Number of unique values
        * "size": Size of the group (including null values)

        Callable:
        Any callable function that returns a single value, such as:
        * sum: Compute the sum of the group.
        * len: Count the number of elements in the group.
        * min: Get the minimum value in the group.
        * max: Get the maximum value in the group.
        * list: Convert group items into a list.
        * set: Convert group items into a set.
        * any: Check if any item in the group evaluates to True.
        * all: Check if all items in the group evaluate to True.
        * lambda functions are also supported such as
            * to compute the range: lambda x: x.max() - x.min()
            * to concatenate strings: lambda x: ''.join(x)

    strict_mode : bool, optional
        If True, all columsn not in groupby must have an aggregation definition.
        It then raises an error if any column in the DataFrame is not in the
        groupby_columns or aggregation definition. Defaults to True.

    Returns
    -------
    pd.DataFrame
        The collapsed DataFrame.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'patient_id': [1, 1, 2, 2],
    ...     'treatment': ['A', 'B', 'A', 'A'],
    ...     'value': [10, 20, 10, 30]
    ... })
    >>> collapse(df, ['patient_id'], {'treatment': list, 'value': 'sum'})
       patient_id treatment  value
    0           1    [A, B]     30
    1           2    [A, A]     40

    >>> collapse(df, ['patient_id'], {'treatment': list, 'value': ['sum', 'count']})
       patient_id treatment_list  value_sum  value_count
    0           1         [A, B]         30            2
    1           2         [A, A]         40            2

    """
    if strict_mode and isinstance(aggregation, dict):
        all_columns = set(df.columns)
        groupby_set = set(groupby_columns)
        aggregation_set = set(aggregation.keys())

        # Check for columns that are neither in groupby nor in aggregation
        undefined_columns = all_columns - (groupby_set | aggregation_set)
        if undefined_columns:
            raise ValueError(
                "Strict mode is enabled, and the following columns are missing"
                f"from the aggregation definition: {undefined_columns}"
            )

    # Perform the aggregation
    agg_df = df.groupby(groupby_columns).agg(aggregation)

    # Flatten multi-level column index if present
    if isinstance(agg_df.columns, pd.MultiIndex):
        agg_df.columns = [
            "_".join(col).strip() for col in agg_df.columns.values
        ]

    return agg_df.reset_index()


def group_statistics(
    df: pd.DataFrame,
    group_column: str,
    target_columns: List[str],
    aggregation: Union[str, callable],
) -> pd.DataFrame:
    """
    Adds statistical information to a DataFrame based on a grouping column.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    group_column : str
        The column by which the DataFrame will be grouped.
    target_columns : List[str]
        The columns on which the aggregation will be performed.
    aggregation : Union[str, Callable]
        The aggregation strategy to apply.

    Returns
    -------
    pd.DataFrame
        The DataFrame enriched with the statistical information.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'patient_id': [1, 2, 3, 4, 5, 6, 7, 8],
    ...     'age_group': ['young', 'young', 'old', 'old', 'young', 'old', 'young', 'old'],
    ...     'value': [10, 20, 25, 30, 5, 50, 15, 40]
    ... })

    >>> result = group_statistics(df, 'age_group', ['value'], 'mean')
    >>> group_statistics(result, 'age_group', ['value'], 'std')
       patient_id age_group  value  age_group_value_mean  age_group_value_std
    0           1     young     10                 12.50             6.454972
    1           2     young     20                 12.50             6.454972
    2           3       old     25                 36.25            11.086779
    3           4       old     30                 36.25            11.086779
    4           5     young      5                 12.50             6.454972
    5           6       old     50                 36.25            11.086779
    6           7     young     15                 12.50             6.454972
    7           8       old     40                 36.25            11.086779

    >>> df = pd.DataFrame({
    ...     'patient_id': [1, 2, 3, 4],
    ...     'ag': ['young', 'young', 'old', 'old'],
    ...     'value': [10, 20, 25, 30],
    ...     'weight': [50, 60, 70, 80]
    ... })

    >>> group_statistics(df, 'ag', ['value', 'weight'], 'mean')
       patient_id     ag  value  weight  ag_value_mean  ag_weight_mean
    0           1  young     10      50           15.0            55.0
    1           2  young     20      60           15.0            55.0
    2           3    old     25      70           27.5            75.0
    3           4    old     30      80           27.5            75.0

    """

    # Compute the statistics and reset index
    stats = df.groupby(group_column)[target_columns].transform(aggregation)
    stats.columns = [
        f"{group_column}_{col}_{aggregation}" for col in stats.columns
    ]

    # Add the statistics back to the original DataFrame
    return pd.concat([df, stats], axis=1)


def impute(
    df: pd.DataFrame,
    missing_values: Union[str, int, float] = np.nan,
    strategy: str = "mean",
    fill_value: Optional[Union[str, int, float]] = None,
    columns: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Impute missing values in a DataFrame. Note that this function will impute
    only using local information, i.e. the imputed values will be calculated
    based on the values in the dataset at the node. It will not calculate
    global statistics and impute based on those.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    missing_values : Union[str, int, float], default='NaN'
        The placeholder for the missing values.
    strategy : str, default='mean'
        The imputation strategy. Options include "mean", "median", "most_frequent", and "constant".
    fill_value : Union[str, int, float], default=None
        When strategy == "constant", fill_value is used to replace all missing values.
    columns : List[str], default=None
        List of columns to apply the imputation to. If None, imputation is applied to all columns.

    Returns
    -------
    pd.DataFrame
        DataFrame with imputed values.

    Example
    --------
    >>> import pandas as pd
    >>> import numpy as np
    >>> df = pd.DataFrame({
    ...     'A': [1, 2, np.nan, 4, 5],
    ...     'B': [5, 4, 3, 2, np.nan],
    ...     'C': [3, np.nan, np.nan, np.nan, np.nan]
    ... })
    >>> impute(df)
         A    B    C
    0  1.0  5.0  3.0
    1  2.0  4.0  3.0
    2  3.0  3.0  3.0
    3  4.0  2.0  3.0
    4  5.0  3.5  3.0
    """

    if columns is None:
        columns = df.columns

    for col in columns:
        if strategy == "mean":
            imputed_value = df[col].mean()
        elif strategy == "median":
            imputed_value = df[col].median()
        elif strategy == "most_frequent":
            imputed_value = df[col].mode().iloc[0]
        elif strategy == "constant":
            imputed_value = fill_value
        else:
            raise ValueError(f"Invalid strategy: {strategy}")

        df[col].replace({missing_values: imputed_value}, inplace=True)

    return df


def filter_by_date(
    df: pd.DataFrame,
    datetime_column: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keep_between: bool = True,
    fmt: Optional[str] = None,
) -> pd.DataFrame:
    """
    Filters a DataFrame based on a datetime column within a given start and end date.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    datetime_column : str
        The column containing datetime information.
    start_date : Optional[str]
        The start date for filtering. Format should follow `fmt`.
    end_date : Optional[str]
        The end date for filtering. Format should follow `fmt`.
    keep_between : bool, default=True
        If True, keep rows between start and end date. If False, keep rows outside the interval.
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
    >>> filter_by_date(df, 'date', start_date='2021-01-02', end_date='2021-01-03')
            date  value
    1 2021-01-02      2
    2 2021-01-03      3
    >>> filter_by_date(df, 'date', start_date='2021-01-02', end_date='2021-01-03',
    ... keep_between=False)
            date  value
    0 2021-01-01      1
    3 2021-01-04      4
    """
    if start_date is None and end_date is None:
        raise ValueError(
            "At least one of start_date or end_date must be provided."
        )

    # Convert the datetime_column to datetime type
    df[datetime_column] = pd.to_datetime(df[datetime_column], format=fmt)

    if start_date:
        start_date = pd.Timestamp(start_date)

    if end_date:
        end_date = pd.Timestamp(end_date)

    if keep_between:
        if start_date and end_date:
            mask = (df[datetime_column] >= start_date) & (
                df[datetime_column] <= end_date
            )
        elif start_date:
            mask = df[datetime_column] >= start_date
        else:
            mask = df[datetime_column] <= end_date
    else:
        if start_date and end_date:
            mask = (df[datetime_column] < start_date) | (
                df[datetime_column] > end_date
            )
        elif start_date:
            mask = df[datetime_column] < start_date
        else:
            mask = df[datetime_column] > end_date

    return df[mask]


def extract_from_string(
    df: pd.DataFrame,
    column: str,
    pattern: str,
    not_found: Optional[str] = None,
    keep_original: bool = True,
    new_column_name: str = "extracted",
) -> pd.DataFrame:
    """
    Extracts specific patterns from a string column in a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    column : str
        The name of the column containing the string to be processed.
    pattern : str
        The regex pattern to extract.
    not_found : Optional[str], default=None
        The value to insert if the pattern is not found.
    keep_original : bool, default=True
        If True, retains the original column. If False, removes the original column.
    new_column_name : str, default='extracted'
        The name for the new column containing extracted data.

    Returns
    -------
    pd.DataFrame
        The DataFrame with extracted information.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({
    ...     'text': ['apple_123', 'banana_456', 'cherry']
    ... })
    >>> extract_from_string(df, 'text', r'_(\d+)', not_found=0,
    ... new_column_name='numbers')
             text numbers
    0   apple_123     123
    1  banana_456     456
    2      cherry       0
    """
    extracted_data = (
        df[column].str.extract(pattern, expand=False).fillna(not_found)
    )
    df[new_column_name] = extracted_data

    if not keep_original:
        df.drop(columns=[column], inplace=True)

    return df
