import json
from typing import BinaryIO, Any


def deserialize(file: BinaryIO) -> Any:
    """
    Deserialize data from a file using JSON

    Parameters
    ----------
    file: BinaryIO
        The file to deserialize the data from

    Returns
    -------
    Any
        The deserialized data
    """
    return json.load(file)
