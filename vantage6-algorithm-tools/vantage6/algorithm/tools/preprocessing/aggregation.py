"""
This module provides functions to perform advanced aggregation operations on
Pandas DataFrames. It is designed to offer flexible yet simple tools to
collapse a DataFrame using various aggregation techniques, and to enrich a
DataFrame with statistical information based on a given grouping.

Functions
---------
- `collapse`: Collapses a DataFrame by grouping by one or more columns and
  aggregating the rest according to specified methods. This function offers
  a wide variety of aggregation strategies ranging from common statistical
  methods to custom callable functions.

- `group_statistics`: Adds statistical information to a DataFrame based on
  specified grouping columns and target columns for aggregation. The function
  allows for customization of the prefix used in the resulting column names.

"""

from typing import Dict, List, Optional, Union

import pandas as pd


def collapse(
    df: pd.DataFrame,
    group_columns: Union[str, List[str]],
    aggregation: Union[
        str,
        callable,
        Dict[str, Union[str, callable, List[Union[str, callable]]]],
    ],
    default_aggregation: Optional[Union[str, callable]] = None,
    strict_mode: bool = True,
) -> pd.DataFrame:
    """
    Collapses a DataFrame by grouping by one or more columns and aggregating
    the rest.

    Parameters:
    -----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : str or List[str]
        Columns by which the DataFrame will be grouped.
    aggregation : str, callable, or Dict
        The aggregation strategy to apply. Can be a string to apply to all
        columns, or a dictionary specifying the aggregation for each column.
        For complex type definitions, refer to the function signature.

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
        * lambda functions are also supported such as:
            * to compute the range: lambda x: x.max() - x.min()
            * to concatenate strings: lambda x: ''.join(x)

    default_aggregation : str or callable, optional
        Default aggregation strategy to apply to columns not explicitly
        mentioned. Only relevant when aggregation is a dictionary.
    strict_mode : bool, optional
        If True, all columns not in groupby must have an aggregation
        definition. An error is raised otherwise. Defaults to True.

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

    >>> collapse(df, ['patient_id'], {'treatment': list, 'value': [
    ... 'sum', 'count']})
       patient_id treatment_list  value_sum  value_count
    0           1         [A, B]         30            2
    1           2         [A, A]         40            2

    """
    assert default_aggregation is None or isinstance(
        aggregation, dict
    ), "If default_aggregation is not None, aggregation must be a dictionary."

    if (
        strict_mode
        and isinstance(aggregation, dict)
        and default_aggregation is None
    ):
        all_columns = set(df.columns)
        groupby_set = set(group_columns)
        aggregation_set = set(aggregation.keys())

        # Check for columns that are neither in groupby nor in aggregation
        undefined_columns = all_columns - (groupby_set | aggregation_set)
        if undefined_columns:
            raise ValueError(
                "Strict mode is enabled, and the following columns are missing"
                f"from the aggregation definition: {undefined_columns}"
            )

    # Set default aggregation if not specified
    if isinstance(aggregation, dict) and default_aggregation is not None:
        aggregation = {
            col: aggregation.get(col, default_aggregation)
            for col in df.columns
            if col not in group_columns
        }

    # Perform the aggregation
    agg_df = df.groupby(group_columns).agg(aggregation)

    # Flatten multi-level column index if present
    if isinstance(agg_df.columns, pd.MultiIndex):
        agg_df.columns = [
            "_".join(col).strip() for col in agg_df.columns.values
        ]

    return agg_df.reset_index()


def group_statistics(
    df: pd.DataFrame,
    group_columns: str,
    target_columns: List[str],
    aggregation: Union[str, callable],
    prefix: str = None,
) -> pd.DataFrame:
    """
    Adds statistical information to a DataFrame based on a grouping column.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : str, List[str]
        The column(s) by which the DataFrame will be grouped.
    target_columns : str, List[str]
        The column(s) on which the aggregation will be performed.
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
    ...     'age_group': ['young', 'young', 'old', 'old', 'young', 'old',
    ...                   'young', 'old'],
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
    stats = pd.DataFrame(
        df.groupby(group_columns)[target_columns].transform(aggregation)
    )

    prefix = group_columns if prefix is None else prefix
    if prefix:
        prefix = f"{prefix}_" if not prefix.endswith("_") else prefix
    stats.columns = [f"{prefix}{col}_{aggregation}" for col in stats.columns]

    # Add the statistics back to the original DataFrame
    return pd.concat([df, stats], axis=1)
