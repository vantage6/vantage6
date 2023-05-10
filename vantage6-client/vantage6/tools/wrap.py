import os
import pickle
import importlib

from types import ModuleType

from typing import BinaryIO, Any, Generator

from vantage6.tools import deserialization, serialization
from vantage6.tools.util import info, warn, error
from vantage6.tools.data_format import DataFormat
from vantage6.tools.exceptions import DeserializationException

_DATA_FORMAT_SEPARATOR = '.'
_MAX_FORMAT_STRING_LENGTH = 10


def wrap_algorithm(module: str) -> None:
    """
    Wrap an algorithm module to provide input and output handling for the
    vantage6 infrastructure.

    Data is received in the form of files, whose location should be
    specified in the following environment variables:
    - ``INPUT_FILE``: input arguments for the algorithm
    - ``OUTPUT_FILE``: location where the results of the algorithm should
        be stored
    - ``TOKEN_FILE``: access token for the vantage6 server REST api
    - ``DATABASE_URI``: either a database endpoint or path to a csv file.

    The wrapper is able to parse a number of input file formats. The
    available formats can be found in
    `vantage6.tools.data_format.DataFormat`. When the input is not pickle
    (legacy), the format should be specified in the first bytes of the
    input file, followed by a '.'.

    It is also possible to specify the desired output format. This is done
    by including the parameter 'output_format' in the input parameters.
    Again, the list of possible output formats can be found in
    `vantage6.tools.data_format.DataFormat`.

    It is still possible that output serialization will fail even if the
    specified format is listed in the DataFormat enum. Algorithms can in
    principle return any python object, but not every serialization format
    will support arbitrary python objects. When dealing with unsupported
    algorithm output, the user should use 'pickle' as output format, which
    is the default.

    The other serialization formats support the following algorithm output:
    - built-in primitives (int, float, str, etc.)
    - built-in collections (list, dict, tuple, etc.)
    - pandas DataFrames

    Parameters
    ----------
    module : str
        Python module name of the algorithm to wrap.
    load_data : bool, optional
        Whether to load the data into a pandas DataFrame or not, by default
        True
    """
    info(f"wrapper for {module}")

    # read input from the mounted input file.
    input_file = os.environ["INPUT_FILE"]
    info(f"Reading input file {input_file}")
    input_data = load_input(input_file)

    # make the actual call to the method/function
    info("Dispatching ...")
    output = _run_algorithm_method(input_data, module)

    # write output from the method to mounted output file. Which will be
    # transferred back to the server by the node-instance.
    output_file = os.environ["OUTPUT_FILE"]
    info(f"Writing output to {output_file}")

    output_format = input_data.get('output_format', None)
    _write_output(output_format, output, output_file)


def _run_algorithm_method(input_data: dict, module: ModuleType) -> Any:
    """
    Load the algorithm module and call the correct method to run an algorithm.

    Parameters
    ----------
    input_data : dict
        The input data that is passed to the algorithm. This should at least
        contain the key 'method' which is the name of the method that should be
        called. Another often used key is 'master' which indicates that this
        container is a master container. Other keys depend on the algorithm.
    module : ModuleType
        The module that contains the algorithm.

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
        exit(1)

    # in case of a master container, we have to do a little extra
    method_name = input_data["method"]

    # attempt to load the method
    try:
        method = getattr(lib, method_name)
    except AttributeError:
        warn(f"Method '{method_name}' not found!\n")
        exit(1)

    # get the args and kwargs input for this function.
    args = input_data.get("args", [])
    kwargs = input_data.get("kwargs", {})

    # try to run the method
    try:
        result = method(*args, **kwargs)
    except Exception as e:
        warn(f"Error encountered while calling {method_name}: {e}")
        exit(1)

    return result


def load_input(input_file: str) -> Any:
    """
    Try to read the specified data format and deserialize the rest of the
    stream accordingly. If this fails, assume the data format is pickle.

    Parameters
    ----------
    input_file : str
        Path to the input file

    Returns
    -------
    Any
        Deserialized input data

    Raises
    ------
    DeserializationException
        Failed to deserialize input data
    """
    with open(input_file, "rb") as fp:
        try:
            input_data = _read_formatted(fp)
        except DeserializationException:
            info('No data format specified. '
                 'Assuming input data is pickle format')
            fp.seek(0)
            try:
                input_data = pickle.load(fp)
            except pickle.UnpicklingError:
                raise DeserializationException('Could not deserialize input')
    return input_data


def _write_output(output_format: str, output: Any, output_file: str) -> None:
    """
    Write output to output_file using the format from output_format.

    If output_format == None, write output as pickle without indicating format
    (legacy method)

    Parameters
    ----------
    output_format : str
        Data type of the output e.g. 'pickle', 'json', 'csv', 'parquet'
    output : Any
        Output of the algorithm, could by any type
    output_file : str
        Path to the output file
    """
    with open(output_file, 'wb') as fp:
        if output_format:
            # Indicate output format
            fp.write(output_format.encode() + b'.')

            # Write actual data
            output_format = DataFormat(output_format.lower())
            serialized = serialization.serialize(output, output_format)
            fp.write(serialized)
        else:
            # No output format specified, use legacy method
            fp.write(pickle.dumps(output))


def _read_formatted(file: BinaryIO) -> Any:
    """
    Try to read the prescribed data format.

    Parameters
    ----------
    file : BinaryIO
        Input file received from the user.

    Returns
    -------
    Any
        Deserialized input data
    """
    data_format = str.join('', list(_read_data_format(file)))
    data_format = DataFormat(data_format.lower())
    return deserialization.deserialize(file, data_format)


def _read_data_format(file: BinaryIO) -> Generator:
    """
    Try to read the prescribed data format. The data format should be specified
    as follows: DATA_FORMAT.ACTUAL_BYTES. This function will attempt to read
    the string before the period. It will fail if the file is not in the right
    format.

    Parameters
    ----------
    file : BinaryIO
        Input file received from the user.

    Yields
    ------
    Generator
        The data format as a string

    Raises
    ------
    DeserializationException
        The file did not have a data format prepended or a non-unicode string
        was encountered
    """
    success = False

    for _ in range(_MAX_FORMAT_STRING_LENGTH):
        try:
            char = file.read(1).decode()
        except UnicodeDecodeError:
            # We aren't reading a unicode string
            raise DeserializationException('Non unicode string encountered')

        if char == _DATA_FORMAT_SEPARATOR:
            success = True
            break
        else:
            yield char

    if not success:
        # The file didn't have a format prepended
        raise DeserializationException('No data format specified')
