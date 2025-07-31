import importlib
import json
import os
import traceback
from typing import Any

import pyarrow.parquet as pq

from vantage6.common import serialization
from vantage6.common.algorithm_function import is_vantage6_algorithm_func
from vantage6.common.client import deserialization
from vantage6.common.enum import AlgorithmStepType
from vantage6.common.globals import ContainerEnvNames

from vantage6.algorithm.tools.exceptions import DeserializationError
from vantage6.algorithm.tools.util import error, get_action, get_env_var, info


def wrap_algorithm(log_traceback: bool = True) -> None:
    """
    Wrap an algorithm module to provide input and output handling for the
    vantage6 infrastructure.

    Data is received in the form of files, whose location should be
    specified in the following environment variables:

    - ``INPUT_FILE``: contains function arguments for the algorithm. This file should be
      encoded in JSON format.
    - ``OUTPUT_FILE``: location where the results of the algorithm should
      be stored
    - ``DATABASE_URI``: uri of the database that the user requested

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

    info(f"Reading function arguments from file {input_file}")
    arguments = load_input(input_file)

    # make the actual call to the method/function
    method = os.environ[ContainerEnvNames.ALGORITHM_METHOD.value]
    info("Dispatching ...")
    output = _run_algorithm_method(
        method=method,
        arguments=arguments,
        module=module,
        log_traceback=log_traceback,
    )

    # write output from the method to mounted output file. Which will be
    # transferred back to the server by the node-instance.
    output_file = os.environ[ContainerEnvNames.OUTPUT_FILE.value]
    info(f"Writing output to {output_file}")

    _write_output(output, output_file)


def _run_algorithm_method(
    method: str,
    module: str,
    arguments: dict | None = None,
    log_traceback: bool = True,
) -> Any:
    """
    Load the algorithm module and call the correct method to run an algorithm.

    Parameters
    ----------
    method : str
        The name of the method that should be called.
    module : str
        The module that contains the algorithm.
    arguments : dict | None
        Arguments for the algorithm method.
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
    try:
        method_fn = getattr(lib, method)
    except AttributeError:
        error(f"Method '{method}' not found!\n")
        if log_traceback:
            error(traceback.print_exc())
        exit(1)

    # check if the method is decorated with a vantage6 decorator. If it is not,
    # we need to raise an error. It is important to check this, because the decorator
    # gives the algorithm function access to certain data sources.
    if not is_vantage6_algorithm_func(method_fn):
        error(
            f"Method '{method}' is not decorated with a vantage6 decorator. All "
            "algorithm functions should have a decorator such as @federated, "
            "@central, @preprocessing, @data_extraction, etc."
        )
        exit(1)

    # try to run the method
    try:
        result = method_fn(**arguments)
    except Exception as exc:
        error(f"Error encountered while calling {method}: {exc}")
        if log_traceback:
            error(traceback.print_exc())
        exit(1)

    return result


def load_input(input_file: str) -> dict:
    """
    Load the function arguments from the input file.

    Parameters
    ----------
    input_file : str
        File containing the input function arguments

    Returns
    -------
    arguments : dict
        Arguments for the algorithm method

    Raises
    ------
    DeserializationError
        Failed to deserialize input data
    """
    with open(input_file, "rb") as fp:
        try:
            arguments = deserialization.deserialize(fp)
        except DeserializationError as exc:
            raise DeserializationError("Could not deserialize input") from exc
        except json.decoder.JSONDecodeError as exc:
            msg = "Algorithm input arguments file does not contain vaild JSON data!"
            error(msg)
            error("Please check that the task input arguments are JSON serializable.")
            raise DeserializationError(msg) from exc
    return arguments


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
