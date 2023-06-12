import json
import pickle

import pandas as pd
from vantage6.tools.data_format import DataFormat
from vantage6.tools.util import info

_serializers = {}


def serialize(data, data_format: DataFormat):
    """
    Look up serializer for `data_format` and use this to serialize `data`.

    :param data:
    :param data_format:
    :return:
    """
    return _serializers[data_format](data)


def serializer(data_format: DataFormat):
    """
    Register function as serializer by adding it to the `_serializers` map with
    key `data_format`. This function should ideally support a multitude of
    python objects.

    There are two ways to extend serialization functionality:

    1. Create and register a new serialization function for a previously
       unsupported serialization format.
    2. Implement support for additional objects within an existing serializer
       function.

    :param data_format:
    :return:
    """

    def decorator_serializer(func):
        # Register serialization function
        _serializers[data_format] = func

        # Return function without modifications so it can also be run without
        # retrieving it from `_serializers`.
        return func

    return decorator_serializer


@serializer(DataFormat.JSON)
def serialize_to_json(data):
    info(f'Serializing type {type(data)} to json')

    if isinstance(data, pd.DataFrame) | isinstance(data, pd.Series):
        return _serialize_pandas(data)

    return _default_serialization(data)


def _default_serialization(data):
    info('Using default json serialization')
    return json.dumps(data).encode()


def _serialize_pandas(data):
    info('Running pandas json serialization')
    return data.to_json().encode()


@serializer(DataFormat.PICKLE)
def serialize_to_pickle(data):
    info('Serializing to pickle')
    return pickle.dumps(data)
