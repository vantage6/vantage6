import inspect
import sys
from inspect import getmembers, getmodule, isfunction

import pandas as pd

from vantage6.algorithm.tools.preprocessing import (
    aggregation,
    column,
    datetime,
    encoding,
    filtering,
)

modules = [aggregation, column, datetime, encoding, filtering]

funcs = []

# Iterate through the modules and get the functions, excluding private ones and imports
for module in modules:
    funcs += [
        func
        for name, func in getmembers(module, isfunction)
        if not name.startswith("_") and getmodule(func) == module
    ]

func_dict = {f.__name__: f for f in funcs}

# Allow users to import all functions from this module without
# explicitly importing them from the submodules
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
        try:
            data = func(data, **parameters)
        except Exception as e:
            error(
                f"Error while executing preprocessing step '{func_name}': "
                f"{e}. Exiting..."
            )
            sys.exit(1)

    return data
