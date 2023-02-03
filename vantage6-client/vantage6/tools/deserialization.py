import json
from typing import BinaryIO


def deserialize(file: BinaryIO):
    """
    Deserialize data from a file using JSON

    Parameters
    ----------
    file: BinaryIO
        The file to deserialize the data from

    Returns
    -------
    str
        The deserialized data
    """
    return json.load(file)
