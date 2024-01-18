import json
from vantage6.common.globals import STRING_ENCODING


# TODO BvB 2023-02-03: I feel this function could be given a better name. And
# it might not have to be in a separate file.
def serialize(data: any) -> bytes:
    """
    Serialize data using the specified format

    Parameters
    ----------
    data: any
        The data to be serialized

    Returns
    -------
    bytes
        A JSON-serialized and then encoded bytes object representing the data
    """
    return json.dumps(data).encode(STRING_ENCODING)
