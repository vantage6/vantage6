import pandas as pd
import yaml

from pathlib import Path

from vantage6.common import STRING_ENCODING
import vantage6.algorithm.tools.preprocessing.functions as prepro_functions
from vantage6.algorithm.tools.util import error



def preprocess_data(data: pd.DataFrame,
                    preproc_input: list[dict]) -> pd.DataFrame:
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
    # read yaml file to get the preprocessing function information
    preprocess_yaml_file = Path(__file__).parent / 'template.yaml'
    with open(preprocess_yaml_file, encoding=STRING_ENCODING) as yaml_file:
        cfg_preprocessing = yaml.safe_load(yaml_file)

    # loop over the preprocessing steps
    for preprocess_step in preproc_input:
        if not "type" in preprocess_step:
            error("Preprocessing step does not contain a type. Exiting...")
            exit(1)

        type_ = preprocess_step["type"]
        if not type_ in cfg_preprocessing:
            error(f"Unknown preprocessing type '{type_}'. Exiting...")
            exit(1)

        # get preprocessing function
        preprocess_func = getattr(prepro_functions, type_)

        # get the arguments and check that required arguments are present
        # TODO extend with checks on the values of the parameters
        # TODO it would be nice to be able to specify additional checks within
        # the preprocessing function (or in the YAML representation)
        # TODO include optional args
        parameters = preprocess_step.get("parameters", {})
        for param in cfg_preprocessing[type_].get('parameters', []):
            if param["required"] and not param["name"] in parameters:
                error(f"Required parameter '{param['name']}' not "
                      f"provided for preprocessing step '{type_}'. Exiting...")
                exit(1)

        data = preprocess_func(data, **parameters)

    return data
