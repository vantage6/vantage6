import os
import importlib
import traceback
import json
import pyarrow.parquet as pq

from typing import Any

from vantage6.common import serialization
from vantage6.common.client import deserialization
from vantage6.common.globals import ContainerEnvNames
from vantage6.algorithm.tools.util import info, error, get_env_var, get_action
from vantage6.algorithm.tools.exceptions import DeserializationError
from vantage6.common.enum import AlgorithmStepType


def wrap_algorithm(log_traceback: bool = True) -> None:
    """
    Wrap an algorithm module to provide input and output handling for the
    vantage6 infrastructure.

    Data is received in the form of files, whose location should be
    specified in the following environment variables:

    - ``INPUT_FILE``: input arguments for the algorithm. This file should be
      encoded in JSON format.
    - ``OUTPUT_FILE``: location where the results of the algorithm should
      be stored
    - ``TOKEN_FILE``: access token for the vantage6 server REST api
    - ``DATABASE_URI``: uri of the database that the user requested

    The wrapper expects the input file to be a json file. Any other file
    format will result in an error.

    Parameters
    ----------
    module : str
        Python module name of the algorithm to wrap.
    log_traceback: bool
        Whether to print the full error message from algorithms or not, by
        default False. Algorithm developers should set this to False if
        the error messages may contain sensitive information. By default True.
    """
    # get the module name from the environment variable. Note that this env var
    # is set in the Dockerfile and is therefore not encoded.
    module = os.environ.get("PKG_NAME")
    if not module:
        error(
            "No PKG_NAME specified! Make sure that the PKG_NAME environment "
            "variable is specified in the Dockerfile. Exiting..."
        )
        exit(1)
    info(f"wrapper for {module}")

    # Decode environment variables that are encoded by the node.
    _decode_env_vars()

    # read input from the mounted input file.
    input_file = os.environ[ContainerEnvNames.INPUT_FILE.value]

    info(f"Reading input file {input_file}")
    input_data = load_input(input_file)

    # make the actual call to the method/function
    info("Dispatching ...")
    output = _run_algorithm_method(input_data, module, log_traceback)

    # write output from the method to mounted output file. Which will be
    # transferred back to the server by the node-instance.
    output_file = os.environ[ContainerEnvNames.OUTPUT_FILE.value]
    info(f"Writing output to {output_file}")

    _write_output(output, output_file)


def _run_algorithm_method(
    input_data: dict, module: str, log_traceback: bool = True
) -> Any:
    """
    Load the algorithm module and call the correct method to run an algorithm.

    Parameters
    ----------
    input_data : dict
        The input data that is passed to the algorithm. This should at least
        contain the key 'method' which is the name of the method that should be
        called. Other keys depend on the algorithm.
    module : str
        The module that contains the algorithm.
    log_traceback: bool, optional
        Whether to print the full error message from algorithms or not, by
        default False. Algorithm developers should set this to False if
        the error messages may contain sensitive information. By default True.

    Returns
    -------
    Any
        The result of the algorithm.
    """
    # import algorithm module
    try:
        lib = importlib.import_module(module)
        info(f"Module '{module}' imported!")
    except ModuleNotFoundError:
        error(f"Module '{module}' can not be imported! Exiting...")
        if log_traceback:
            error(traceback.print_exc())
        exit(1)

    # get algorithm method and attempt to load it
    method_name = input_data["method"]
    try:
        method = getattr(lib, method_name)
    except AttributeError:
        error(f"Method '{method_name}' not found!\n")
        if log_traceback:
            error(traceback.print_exc())
        exit(1)

    # get the args and kwargs input for this function.
    args = input_data.get("args", [])
    kwargs = input_data.get("kwargs", {})

    # try to run the method
    try:
        result = method(*args, **kwargs)
    except Exception as e:
        error(f"Error encountered while calling {method_name}: {e}")
        if log_traceback:
            error(traceback.print_exc())
        exit(1)

    return result


def load_input(input_file: str) -> Any:
    """
    Load the input from the input file.

    Parameters
    ----------
    input_file : str
        File containing the input

    Returns
    -------
    input_data : Any
        Input data for the algorithm

    Raises
    ------
    DeserializationError
        Failed to deserialize input data
    """
    with open(input_file, "rb") as fp:
        try:
            input_data = deserialization.deserialize(fp)
        except DeserializationError as exc:
            raise DeserializationError("Could not deserialize input") from exc
        except json.decoder.JSONDecodeError as exc:
            msg = "Algorithm input file does not contain vaild JSON data!"
            error(msg)
            error("Please check that the task input is JSON serializable.")
            raise DeserializationError(msg) from exc
    return input_data


def _write_output(output: Any, output_file: str) -> None:
    """
    Write output to output file.

    In case the result needs to be sent to the server the output file should contain
    valid JSON data. This is because the node will read the output file and send the
    data to the server.

    In the case we are building a session, the output of the algorithm is expected to
    be a parquet table. In this case, the output file should contain the parquet data.

    Parameters
    ----------
    output : Any
        Output of the algorithm
    output_file : str
        Path to the output file
    """
    action = get_action()

    if action in [AlgorithmStepType.DATA_EXTRACTION, AlgorithmStepType.PREPROCESSING]:
        # If the action is data extraction or preprocessing, the output should be a
        # parquet table. In this case, the output file should contain the parquet data.
        # It is important that we do not alter this format as it would complicate
        # writing algorithms that are not using this wrapper. So we use the standard
        # paruet serialization method.
        pq.write_table(output, output_file)
    else:

        with open(output_file, "wb") as fp:
            serialized = serialization.serialize(output)
            fp.write(serialized)


def _decode_env_vars() -> None:
    """
    Decode environment variables that are encoded by the node

    Note that environment variables may be present that are not specific to vantage6,
    such as HOME, PATH, etc. These are not encoded by the node and should not be
    decoded here. The `get_env_var` function handles these properly so that the
    original value is returned if the environment variable is not encoded.
    """
    for env_var in os.environ:
        os.environ[env_var] = get_env_var(env_var)
