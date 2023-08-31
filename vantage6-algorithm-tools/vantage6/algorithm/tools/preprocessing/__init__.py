import pandas as pd

from vantage6.common import STRING_ENCODING
import vantage6.algorithm.tools.preprocessing.functions as prepro_functions
from vantage6.algorithm.tools.util import error, info


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

    # allow some mistakes in input format on the user side
    if isinstance(preproc_input, dict):
        preproc_input = [preproc_input]

    available_functions = [
        name for name, obj in prepro_functions.__dict__.items() if callable(obj)
    ]

    # loop over the preprocessing steps
    for preprocess_step in preproc_input:
        func_name = (
            preprocess_step["type"]
            if "type" in preprocess_step
            else list(preprocess_step.keys())[0]
        )

        if func_name not in available_functions:
            error(f"Unknown preprocessing function '{func_name}'. Exiting...")
            raise ValueError(f"Unknown preprocessing function '{func_name}'")

        func = getattr(prepro_functions, func_name)

        if func_name in preprocess_step:
            parameters = preprocess_step[func_name]
        else:
            parameters = preprocess_step.get("parameters", {})

        if isinstance(parameters, dict):
            data = func(data, **parameters)
        elif isinstance(parameters, str):
            data = func(data, *[parameters])
        else:
            data = func(data, *parameters)

    return data
