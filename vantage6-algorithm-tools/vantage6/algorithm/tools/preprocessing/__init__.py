import inspect
import sys

import pandas as pd

from vantage6.algorithm.tools.preprocessing.aggregation import (
    collapse,
    group_statistics,
)
from vantage6.algorithm.tools.preprocessing.column import (
    assign_column,
    change_column_type,
    rename_columns,
)
from vantage6.algorithm.tools.preprocessing.datetime import (
    calculate_age,
    timedelta,
    to_datetime,
    to_timedelta,
)
from vantage6.algorithm.tools.preprocessing.encoding import (
    discretize_column,
    encode,
    extract_from_string,
    impute,
    min_max_scale,
    one_hot_encode,
    standard_scale,
)
from vantage6.algorithm.tools.preprocessing.filter import (
    drop_columns,
    drop_columns_by_index,
    filter_by_date,
    filter_range,
    select_columns,
    select_columns_by_index,
    select_rows,
)
from vantage6.algorithm.tools.util import error

funcs = [
    assign_column,
    calculate_age,
    change_column_type,
    collapse,
    discretize_column,
    drop_columns,
    drop_columns_by_index,
    encode,
    extract_from_string,
    filter_by_date,
    filter_range,
    group_statistics,
    impute,
    min_max_scale,
    one_hot_encode,
    rename_columns,
    select_columns,
    select_columns_by_index,
    select_rows,
    standard_scale,
    timedelta,
    to_datetime,
    to_timedelta,
]
func_dict = {f.__name__: f for f in funcs}

__all__ = list(func_dict.keys())


def preprocess_data(
    data: pd.DataFrame, preproc_input: list[dict]
) -> pd.DataFrame:
    """
    Execute any data preprocessing steps here that the user may have specified

    Parameters
    ----------
    data : pd.DataFrame
        Data to preprocess
    preproc_input : list[dict]
        Desired preprocessing steps defined by user

    Returns
    -------
    pd.DataFrame
        Preprocessed data
    """
    if isinstance(preproc_input, dict):
        preproc_input = [preproc_input]

    # loop over the preprocessing steps
    for preprocess_step in preproc_input:
        if "function" not in preprocess_step:
            error(
                "Preprocessing step does not contain a 'function' to run. "
                "Exiting..."
            )
            sys.exit(1)

        func_name = preprocess_step["function"]

        # get preprocessing function
        if func_name in func_dict:
            func = func_dict.get(func_name)
        else:
            error(
                f"Unknown preprocessing type '{func_name}' defined. Please "
                "check your preprocessing input. Exiting..."
            )
            sys.exit(1)

        # extract the parameters
        parameters = preprocess_step.get("parameters", {})

        # check if the function parameters without default values have been
        # provided - except for the first parameter (the pandas dataframe),
        # which is provided by the infrastructure
        sig = inspect.signature(func)
        first_arg_name = next(iter(sig.parameters))
        for param in sig.parameters.values():
            if (
                param.name != first_arg_name
                and param.default is param.empty
                and param.name not in preprocess_step["parameters"]
            ):
                error(
                    f"Parameter '{param.name}' not provided for "
                    f"preprocessing step '{func_name}'. Exiting..."
                )
                sys.exit(1)

        # execute the preprocessing function
        data = func(data, **parameters)

    return data
