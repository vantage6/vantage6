from io import BufferedReader
import json
from typing import Any


def deserialize(file: BufferedReader) -> Any:
    """
    Deserialize data from a file using JSON

    Parameters
    ----------
    file: BufferedReader
        The file to deserialize the data from

    Returns
    -------
    Any
        The deserialized data
    """
    return json.load(file)
