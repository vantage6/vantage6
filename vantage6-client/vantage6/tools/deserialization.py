import json
import pickle

from vantage6.tools.data_format import DataFormat

_deserializers = {}


def deserialize(file, data_format: DataFormat):
    """
    Lookup data_format in deserializer mapping and return the associated
    function.

    :param file:
    :param data_format:
    :return:
    """
    try:
        return _deserializers[data_format](file)
    except KeyError:
        raise Exception(
            f'Deserialization of {data_format} has not been implemented.'
        )


def deserializer(data_format):
    """
    Register function as deserializer by adding it to the `_deserializers` map
    with key `data_format`.

    These functions should receive a file-like as input and provide the data as
    output in the format specified with the decorator.

    :param data_format:
    :return:
    """

    def decorator_deserializer(func):
        # Register deserialization function
        _deserializers[data_format] = func

        # Return function without modifications so it can also be run without
        # retrieving it from `_deserializers`.
        return func

    return decorator_deserializer


@deserializer(DataFormat.JSON)
def deserialize_json(file):
    return json.load(file)


@deserializer(DataFormat.PICKLE)
def deserialize_pickle(file):
    return pickle.load(file)
