"""
This module provides functions to perform advanced aggregation operations on
Pandas DataFrames. It is designed to offer flexible yet simple tools to
collapse a DataFrame using various aggregation techniques, and to enrich a
DataFrame with statistical information based on a given grouping.
"""

import pandas as pd

from vantage6.algorithm.decorator.action import preprocessing
from vantage6.algorithm.decorator.data import dataframe
from vantage6.algorithm.tools.exceptions import UserInputError


@preprocessing
@dataframe(1)
def collapse(
    df: pd.DataFrame,
    group_columns: list[str],
    aggregation_strategy: str | None = None,
    aggregation_dict: dict | None = None,
    default_aggregation: str | None = None,
    strict_mode: bool = True,
) -> pd.DataFrame:
    """
    Collapses a DataFrame by grouping by one or more columns and aggregating
    the rest.

    Parameters
    -----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : list[str]
        Columns by which the DataFrame will be grouped.
    aggregation_strategy : str | None
        The aggregation strategy to apply. This strategy is applied to all columns. If
        you want to apply different strategies to different columns, use the
        aggregation_dict parameter (either this or aggregation should be provided).

        Following aggregation strategies are supported:

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

    aggregation_dict: dict | None
        A dictionary for specific manner of  aggregation per column. Each column can
        be aggregated in the same ways as the string aggregation strategies. Either this
        variable or aggregation should be provided.
    default_aggregation : str | None
        Used for left-over columns when column-specific aggregation is
        specified. Only used when aggregation_dict is provided.
    strict_mode : bool
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

    if aggregation_strategy is None and aggregation_dict is None:
        raise UserInputError(
            "Either aggregation_strategy or aggregation_dict must be provided."
        )
    elif aggregation_strategy is not None and aggregation_dict is not None:
        raise UserInputError(
            "Only one of aggregation_strategy or aggregation_dict must be provided."
        )

    # Convert string aggregation keywords to actual functions
    aggregation_mapping = {
        "len": len,
        "list": list,
        "set": set,
        "any": any,
        "all": all,
    }

    # Helper function to apply mapping
    def map_aggregation(agg):
        if isinstance(agg, str) and agg in aggregation_mapping:
            return aggregation_mapping[agg]
        elif isinstance(agg, list):
            return [map_aggregation(a) for a in agg]
        return agg

    # If a single string is provided, map to function, otherwise, apply
    # mapping to dict
    if aggregation_strategy is not None:
        aggregation = map_aggregation(aggregation_strategy)
    else:
        aggregation = {
            col: map_aggregation(agg) for col, agg in aggregation_dict.items()
        }

    if strict_mode and isinstance(aggregation, dict) and default_aggregation is None:
        all_columns = set(df.columns)
        groupby_set = set(group_columns)
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
@dataframe(1)
def group_statistics(
    df: pd.DataFrame,
    group_columns: list[str],
    target_columns: list[str],
    aggregation_strategy: str,
    prefix: str | None = None,
) -> pd.DataFrame:
    """
    Adds statistical information to a DataFrame based on a grouping column.

    Parameters
    ----------
    df : pd.DataFrame
        The input DataFrame.
    group_columns : list[str]
        The columns by which the DataFrame will be grouped.
    target_columns : list[str]
        The columns on which the aggregation will be performed.
    aggregation_strategy : str
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
        df.groupby(group_columns)[target_columns].transform(aggregation_strategy)
    )

    prefix = group_columns if prefix is None else prefix
    if prefix:
        prefix = f"{prefix}_" if not prefix.endswith("_") else prefix
    stats.columns = [f"{prefix}{col}_{aggregation_strategy}" for col in stats.columns]

    # Add the statistics back to the original DataFrame
    return pd.concat([df, stats], axis=1)
