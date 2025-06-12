"""
This module provides functions to perform advanced aggregation operations on
Pandas DataFrames. It is designed to offer flexible yet simple tools to
collapse a DataFrame using various aggregation techniques, and to enrich a
DataFrame with statistical information based on a given grouping.
"""

from typing import Callable
import pandas as pd

from vantage6.algorithm.decorator.action import preprocessing
from vantage6.algorithm.decorator.data import data
from vantage6.algorithm.tools.exceptions import UserInputError


@preprocessing
@data(1)
def collapse(
    df: pd.DataFrame,
    group_columns: str | list[str],
    aggregation: str | Callable | dict[str, str | Callable | list[str | Callable]],
    default_aggregation: str | Callable | None = None,
    strict_mode: bool = True,
) -> pd.DataFrame:
    """
    Collapses a DataFrame by grouping by one or more columns and aggregating
    the rest.

    Parameters
    -----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : str or list[str]
        Columns by which the DataFrame will be grouped.
    aggregation : str, callable, or dict
        The aggregation strategy to apply. Can be a string to apply to all
        columns, or a dictionary specifying the aggregation for each column.
        For complex type definitions, refer to the function signature.

        Valid aggregation strategies:

        String:

        * "sum"
        * "mean"
        * "min"
        * "max"
        * "count", "len": Count the number of elements in the group.
        * "std": Standard Deviation
        * "var": Variance
        * "first": First non-null value in the group
        * "last": Last non-null value in the group
        * "nunique": Number of unique values
        * "size": Size of the group (including null values)
        * "list": Convert group items into a list.
        * "set": Convert group items into a set.
        * "any": Check if any item in the group evaluates to True.
        * "all": Check if all items in the group evaluate to True.
    default_aggregation : str or callable, optional
        Used for left-over columns when column-specific aggregation is
        specified. Only relevant when aggregation is a dictionary.
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
    # Convert string aggregation keywords to actual functions
    aggregation_mapping = {
        "len": len,
        "list": list,
        "set": set,
        "any": any,
        "all": all,
    }

    # Assert conditions for default_aggregation
    assert default_aggregation is None or isinstance(
        aggregation, dict
    ), "If default_aggregation is not None, aggregation must be a dictionary."

    # Helper function to apply mapping
    def map_aggregation(agg):
        if isinstance(agg, str) and agg in aggregation_mapping:
            return aggregation_mapping[agg]
        elif isinstance(agg, list):
            return [map_aggregation(a) for a in agg]
        return agg

    # If a single string is provided, map to function, otherwise, apply
    # mapping to dict
    if isinstance(aggregation, str):
        aggregation = map_aggregation(aggregation)
    elif isinstance(aggregation, dict):
        aggregation = {col: map_aggregation(agg) for col, agg in aggregation.items()}

    if strict_mode and isinstance(aggregation, dict) and default_aggregation is None:
        all_columns = set(df.columns)
        groupby_set = set(
            group_columns if isinstance(group_columns, list) else [group_columns]
        )
        aggregation_set = set(aggregation.keys())

        undefined_columns = all_columns - (groupby_set | aggregation_set)
        if undefined_columns:
            raise UserInputError(
                "Strict mode is enabled, and the following columns are missing"
                f" from the aggregation definition: {undefined_columns}"
            )

    # Set default aggregation if not specified and ensure it is a valid
    # operation
    if isinstance(aggregation, dict) and default_aggregation is not None:
        default_aggregation = map_aggregation(default_aggregation)
        aggregation = {
            col: aggregation.get(col, default_aggregation)
            for col in df.columns
            if col not in group_columns
        }

    # Perform the aggregation
    agg_df = df.groupby(group_columns).agg(aggregation)

    # Flatten multi-level column index if present
    if isinstance(agg_df.columns, pd.MultiIndex):
        agg_df.columns = ["_".join(col).strip() for col in agg_df.columns.values]

    return agg_df.reset_index()


@preprocessing
@data(1)
def group_statistics(
    df: pd.DataFrame,
    group_columns: str | list[str],
    target_columns: list[str],
    aggregation: str | Callable,
    prefix: str | None = None,
) -> pd.DataFrame:
    """
    Adds statistical information to a DataFrame based on a grouping column.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : str | list[str]
        The column(s) by which the DataFrame will be grouped.
    target_columns : list[str]
        The column(s) on which the aggregation will be performed.
    aggregation : str | Callable
        The aggregation strategy to apply.
    prefix : str | None, optional
        An optional prefix for the names of new columns.

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
