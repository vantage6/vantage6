"""
This module provides functions for specific operations on Pandas DataFrames.
It focuses on simplifying column renaming and column assignment through dynamic
expressions.
"""

import pandas as pd


def rename_columns(
    df: pd.DataFrame, new_names: dict[str, str]
) -> pd.DataFrame:
    """
    Rename DataFrame columns.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame whose columns you want to rename.
    new_names : dict[str, str]
        A mapping from current column names to new names.

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
    """

    return df.rename(columns=new_names)


def assign_column(
    df: pd.DataFrame, column_name: str, expression: str
) -> pd.DataFrame:
    """
    Create a new column in a DataFrame based on the given expression.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to which a new column will be added.
    column_name : str
        The name of the new column.
    expression : str
        The expression used to create the new column.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with the new column added.

    Raises
    ------
    ValueError
        If the column_name already exists in the DataFrame.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    >>> assign_column(df, "C", "A + B")
       A  B  C
    0  1  3  4
    1  2  4  6
    """
    if column_name in df.columns:
        raise ValueError(f"Column '{column_name}' already exists.")

    new_df = df.copy()
    new_df[column_name] = new_df.eval(expression)
    return new_df


def redefine_column(
    df: pd.DataFrame, column_name: str, expression: str
) -> pd.DataFrame:
    """
    Modify an existing column in a DataFrame based on the given expression.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame whose column will be modified.
    column_name : str
        The name of the existing column to modify.
    expression : str
        The expression used to modify the existing column.

    Returns
    -------
    pandas.DataFrame
        A DataFrame with the modified column.

    Raises
    ------
    ValueError
        If the column_name does not exist in the DataFrame.

    Examples
    --------
    >>> import pandas as pd
    >>> df = pd.DataFrame({"A": [1, 2], "B": [3, 4]})
    >>> df = assign_column(df, "C", "A + B")
    >>> redefine_column(df, "C", "A * B")
       A  B  C
    0  1  3  3
    1  2  4  8
    """
    if column_name not in df.columns:
        raise ValueError(f"Column '{column_name}' does not exist.")

    new_df = df.copy()
    new_df[column_name] = new_df.eval(expression)
    return new_df


def change_column_type(
    df: pd.DataFrame, columns: list[str], target_type: str | type
) -> pd.DataFrame:
    """
    Change DataFrame column data types.

    Parameters
    ----------
    df : pd.DataFrame
        The DataFrame whose columns' data types you want to change.
    columns : list[str]
        List of column names whose data types you want to change.
    target_type : str | type
        The desired data type (either string representation or Python type)
        for the specified columns.

    Returns
    -------
    pandas.DataFrame
        DataFrame with updated column data types.

    Examples
    --------
    >>> df1 = pd.DataFrame({
    ...     'a': ['1', '2'],
    ...     'b': ['3.1', '4.2']
    ... })
    >>> change_column_type(df1, ['a', 'b'], float)
         a    b
    0  1.0  3.1
    1  2.0  4.2

    >>> df2 = pd.DataFrame({
    ...     'category_column': pd.Categorical(['apple', 'banana', 'cherry'])
    ... })
    >>> print("Before conversion:", df2['category_column'].dtype)
    Before conversion: category
    >>> df3 = change_column_type(df2, ['category_column'], str)
    >>> print("After conversion:", df3['category_column'].dtype)
    After conversion: object
    """
    df = df.copy()
    for col in columns:
        if col not in df.columns:
            raise KeyError(f"Column {col} not found in the DataFrame")
        df[col] = df[col].astype(target_type)

    return df
