import datetime
import enum
import json

import logging

import sqlalchemy as sql

from vantage6.backend.common.base import Base
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


def jsonable(value: list[Base] | Base) -> list | dict:
    """
    Convert a (list of) SQLAlchemy instance(s) to native Python objects.

    Parameters
    ----------
    value : list[Base] | Base
        A single SQLAlchemy instance or a list of SQLAlchemy instances

    Returns
    -------
    list | dict
        A single Python object or a list of Python objects

    Raises
    ------
    Exception
        If the value is not an instance of db.Base or a list of db.Base
    """
    if isinstance(value, list):
        return [jsonable(i) for i in value]

    elif isinstance(value, Base):
        log.debug(f"preparing={value}")
        retval = dict()
        mapper = sql.inspect(value.__class__)

        columns = [
            c.key for c in mapper.columns if c.key not in value._hidden_attributes
        ]

        for column in columns:
            column_value = getattr(value, column)

            if isinstance(column_value, enum.Enum):
                column_value = column_value.value
            elif isinstance(column_value, datetime.datetime):
                column_value = column_value.isoformat()
            elif isinstance(column_value, bytes):
                log.debug("decoding bytes!")
                column_value = column_value.decode(STRING_ENCODING)

            retval[column] = column_value

        return retval

    # FIXME: does it make sense to raise an exception or should base types
    #        (or other JSON-serializable types) just be returned as-is?
    raise Exception("value should be instance of db.Base or list!")
