import json

import logging

from vantage6.common.globals import STRING_ENCODING
from vantage6.common import logger_name


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


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
