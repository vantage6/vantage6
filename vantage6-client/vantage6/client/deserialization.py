"""
Module for deserialization of algorithm results.

TODO: Merge with `vantage6.tools.deserialization` in `vantage6-toolkit` and move to `vantage6-common`
"""

import json
import logging
import pickle
from .exceptions import DeserializationException

_DATA_FORMAT_SEPARATOR = '.'
_MAX_FORMAT_STRING_LENGTH = 10

logger = logging.getLogger(__name__)

_deserializers = {}


def deserialize(file, data_format):
    """
    Lookup data_format in deserializer mapping and return the associated
    :param file:
    :param data_format:
    :return:
    """
    try:
        return _deserializers[data_format.lower()](file)
    except KeyError:
        raise Exception(f'Deserialization of {data_format} has not been implemented.')


def deserializer(data_format):
    """
    Register function as deserializer by adding it to the `_deserializers` map with key `data_format`.

    :param data_format:
    :return:
    """

    def decorator_deserializer(func):
        # Register deserialization function
        _deserializers[data_format] = func

        # Return function without modifications so it can also be run without retrieving it from `_deserializers`.
        return func

    return decorator_deserializer


@deserializer('json')
def deserialize_json(file):
    return json.loads(file)


@deserializer('pickle')
def deserialize_pickle(file):
    return pickle.loads(file)


def unpack_legacy_results(result):
    return pickle.loads(result.get("result"))


def load_data(input_bytes: bytes):
    """
    Try to read the specified data format and deserialize the rest of the stream accordingly. If this fails, assume
    the data format is pickle.

    :param input_bytes:
    :return:
    """
    try:
        input_data = _read_formatted(input_bytes)
    except DeserializationException:
        logger.info('No data format specified. Assuming input data is pickle format')
        try:
            input_data = pickle.loads(input_bytes)
        except pickle.UnpicklingError:
            raise DeserializationException('Could not deserialize input')
    return input_data


def _read_formatted(input_bytes):
    data_format = str.join('', list(_read_data_format(input_bytes)))
    return deserialize(input_bytes[len(data_format) + 1:], data_format)


def _read_data_format(input_bytes):
    """
    Try to read the prescribed data format. The data format should be specified as follows: DATA_FORMAT.ACTUAL_BYTES.
    This function will attempt to read the string before the period. It will fail if the file is not in the right
    format.

    :param input_bytes: Input file received from vantage infrastructure.
    :return:
    """
    success = False

    for i in range(_MAX_FORMAT_STRING_LENGTH):
        try:
            char = input_bytes[i:i+1].decode()
        except UnicodeDecodeError:
            # We aren't reading a unicode string
            raise DeserializationException('No data format specified')

        if char == _DATA_FORMAT_SEPARATOR:
            success = True
            break
        else:
            yield char

    if not success:
        # The file didn't have a format prepended
        raise DeserializationException('No data format specified')
