"""
This module provides functions for specific operations on Pandas DataFrames.
It focuses on simplifying column renaming and column assignment through dynamic
expressions.

Functions
---------
- `rename_columns`: Renames DataFrame's columns based on a provided dict or
  list. Supports both direct mapping and indexed renaming of columns.

- `assign_column`: Adds or modifies a DataFrame column using a given
  expression. Permits conditional overwriting of existing columns.
"""

from typing import Dict, List, Union

import pandas as pd


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
        If a list, new column names in order; the length should match the
        number of columns.

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


def assign_column(
    df: pd.DataFrame,
    column_name: str,
    expression: str,
    overwrite: bool = False,
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
