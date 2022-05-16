import json
import pickle

_serializers = {}


def serialize(data, data_format) -> bytes:
    """
    Serialize data using the specified format
    :param data: the data to be serialized
    :param data_format: the desired data format. Valid options are 'json', 'pickle'.
    :return: a bytes-like object in the specified serialization format
    """
    try:
        return _serializers[data_format.lower()](data)
    except KeyError:
        raise Exception(f'Serialization of {data_format} has not been implemented.')


def serializer(data_format):
    """
    Register function as serializer by adding it to the `_serializers` map with key `data_format`.

    :param data_format:
    :return:
    """

    def decorator_serializer(func):
        # Register deserialization function
        _serializers[data_format] = func

        # Return function without modifications so it can also be run without retrieving it from `_serializers`.
        return func

    return decorator_serializer


@serializer('json')
def serialize_json(file) -> bytes:
    return json.dumps(file).encode()


@serializer('pickle')
def serialize_pickle(file) -> bytes:
    return pickle.dumps(file)
