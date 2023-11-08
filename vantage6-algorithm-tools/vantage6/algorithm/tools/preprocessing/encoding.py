"""
This module contains functions for various DataFrame transformations including
min-max scaling, standard scaling, one-hot encoding, and custom encoding. The
functions are designed to be used in a federated setting, where nodes may not
have access to the entire dataset's statistics. Therefore, these functions
require external parameters like minimum and maximum values or means and
standard deviations for scaling operations.
"""

from typing import Dict, List, Optional, Union

import numpy as np
import pandas as pd


def min_max_scale(
    df: pd.DataFrame,
    min_vals: list[float],
    max_vals: list[float],
    columns: list[str] | None = None,
) -> pd.DataFrame:
    """
    Perform min-max scaling on specified columns of a DataFrame using the
    formula (x - min) / (max - min). The function is applied in a federated
    setting, meaning one node does not know the global min and mix. This means
    the minimum and maximum values for each column must be specified.
    If columns are not provided, all columns are scaled and the length of
    min_vals and max_vals must match the number of DataFrame columns.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to scale.
    min_vals : list of float
        List of minimum values for scaling; should match the length of columns.
    max_vals : list of float
        List of maximum values for scaling; should match the length of columns.
    columns : list of str | None, optional
        List of columns to scale; if None, all columns are scaled and the
        length of min_vals and max_vals must match df.columns.

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
    means: list[float],
    stds: list[float],
    columns: list[str] | None = None,
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
    means : list of float
        List of mean values for scaling; should match the length of columns.
    stds : list of float
        List of standard deviation values for scaling; should match the length
        of columns.
    columns : list of str | None, optional
        List of columns to scale; if None, all columns are scaled and the
        length of means and stds must match df.columns.

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
                "Length of means and stds must match the number of DataFrame"
                "columns when columns is None"
            )
        columns = df.columns.tolist()
    else:
        if len(means) != len(stds) or len(means) != len(columns):
            raise ValueError(
                "Length of means and stds must match the number of specified"
                "columns"
            )

    df_scaled = df.copy()
    for col, mean, std in zip(columns, means, stds):
        df_scaled[col] = (df[col] - mean) / std

    return df_scaled


def one_hot_encode(
    df: pd.DataFrame,
    column: str,
    categories: list[str],
    unknown_category: str | None = "unknown",
    drop_original: bool = True,
    prefix: str | None = None,
) -> pd.DataFrame:
    """
    Perform one-hot encoding on a specific column of a DataFrame. As one node
    may not have access to all possible categories in the entire dataset, this
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
    categories : list of str
        List of predefined categories.
    unknown_category : str | None, optional
        Label for unseen categories.
    drop_original : bool, optional
        Whether to drop the original column, default is True.
    prefix : str | None, optional
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

    >>> one_hot_encode(df, 'color', ['red', 'green'], unknown_category='other',
    ...                prefix='col')
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
    columns: list[str],
    mapping: dict,
    unknown_value: str | int = -1,
    raise_on_unknown: bool = False,
) -> pd.DataFrame:
    """
    Custom encoding of DataFrame columns using a provided mapping.

    Parameters
    ----------
    df : pandas.DataFrame
        The DataFrame to encode.
    columns : list of str
        List of column names to be encoded.
    mapping : dict
        Dictionary containing the mapping for encoding. Keys are original
        values and values are the new encoded values.
    unknown_value : str | int
        Value to use for any unknown categories.
    raise_on_unknown : bool
        If True, raises an error when encountering an unknown category.
        Otherwise, uses unknown_value.

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
                f"Unknown categories {unique_vals} encountered in column"
                f"{col}."
            )
        encoded_df[col] = encoded_df[col].apply(
            lambda x: mapping.get(x, unknown_value)
        )

    return encoded_df


def discretize_column(
    df: pd.DataFrame,
    column_name: str,
    bins: Union[int, List[Union[int, float]]],
    labels: List[str] = None,
    right: bool = True,
    include_lowest: bool = False,
    output_column: str = None,
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
    output_column : str, optional
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
    ... "Middle", "Senior", "Old"], output_column="AgeCategory")
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

    if output_column is None:
        output_column = column_name

    new_df[output_column] = new_column
    return new_df


def extract_from_string(
    df: pd.DataFrame,
    column: str,
    pattern: str,
    not_found: str | None = np.nan,
    keep_original: bool = True,
    output_column: str = "extracted",
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
    not_found : str | None, default=np.nan
        The value to insert if the pattern is not found.
    keep_original : bool, default=True
        If True, retains the original column. If False, removes the original
        column.
    output_column : str, default='extracted'
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
    >>> extract_from_string(df, 'text', '_(\\d+)', not_found=0,
    ... output_column='numbers')
             text numbers
    0   apple_123     123
    1  banana_456     456
    2      cherry       0
    """
    extracted_data = (
        df[column].str.extract(pattern, expand=False).fillna(not_found)
    )
    df[output_column] = extracted_data

    if not keep_original:
        df.drop(columns=[column], inplace=True)

    return df


def impute(
    df: pd.DataFrame,
    columns: list[str] | None = None,
    missing_values: str | int | float = np.nan,
    strategy: str = "mean",
    group_columns: list[str] | None = None,
    fill_value: str | int | float | None = None,
) -> pd.DataFrame:
    """
    Impute missing values in a DataFrame. If group_columns are provided, the
    imputation is done within the groups defined by those columns.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    columns : list[str] | None, default=None
        List of columns to apply the imputation to. If None, imputation is
        applied to all columns.
    missing_values : str | int | float, default=np.nan
        The placeholder for the missing values.
    strategy : str, default='mean'
        The imputation strategy. Options include "mean", "median",
        "most_frequent", and "constant".
    group_columns : list[str] | None, default=None
        List of columns to group by for imputation.
    fill_value : str | int | float | None, default=None
        When strategy == "constant", fill_value is used to replace all missing
        values.

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

    >>> df = pd.DataFrame({
    ...     'Group': ['A', 'A', 'B', 'B', 'B'],
    ...     'Value': [1, np.nan, 2, np.nan, 3],
    ... })
    >>> impute(df, strategy='mean', group_columns=['Group'], columns=['Value'])
      Group  Value
    0     A    1.0
    1     A    1.0
    2     B    2.0
    3     B    2.5
    4     B    3.0
    """
    columns = [columns] if isinstance(columns, str) else columns
    if columns is None:
        columns = df.columns

    def impute_group(group):
        for col in columns:
            if col not in group.columns:
                continue

            if strategy == "mean":
                imputed_value = group[col].mean()
            elif strategy == "median":
                imputed_value = group[col].median()
            elif strategy == "most_frequent":
                imputed_value = group[col].mode().iloc[0]
            elif strategy == "constant":
                imputed_value = fill_value
            else:
                raise ValueError(f"Invalid strategy: {strategy}")

            group[col].replace({missing_values: imputed_value}, inplace=True)
        return group

    # Apply the imputation
    if group_columns:
        df = df.groupby(group_columns, group_keys=False).apply(impute_group)
    else:
        df = impute_group(df)

    return df
