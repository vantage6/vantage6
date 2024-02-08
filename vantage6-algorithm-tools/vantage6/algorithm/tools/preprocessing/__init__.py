import pandas as pd
import inspect

import vantage6.algorithm.tools.preprocessing.functions as prepro_functions
from vantage6.algorithm.tools.util import error


def preprocess_data(data: pd.DataFrame, preproc_input: list[dict]) -> pd.DataFrame:
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
    # loop over the preprocessing steps
    for preprocess_step in preproc_input:
        if "function" not in preprocess_step:
            error(
                "Preprocessing step does not contain a 'function' to run. " "Exiting..."
            )
            exit(1)

        func_name = preprocess_step["function"]

        # get preprocessing function
        try:
            preprocess_func = getattr(prepro_functions, func_name)
        except AttributeError:
            error(
                f"Unknown preprocessing type '{func_name}' defined. Please "
                "check your preprocessing input. Exiting..."
            )
            exit(1)

        # check if the function parameters without default values have been
        # provided - except for the first parameter (the pandas dataframe),
        # which is provided by the infrastructure
        sig = inspect.signature(preprocess_func)
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
                exit(1)

        # execute the preprocessing function
        parameters = preprocess_step.get("parameters", {})
        data = preprocess_func(data, **parameters)

    return data
