"""
This module contains several preprocessing functions that may be used to
prepare the data for the algorithm.
"""

import pandas as pd


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
