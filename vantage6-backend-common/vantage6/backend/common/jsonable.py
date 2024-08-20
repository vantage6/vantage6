import datetime
import enum

import sqlalchemy as sql
from sqlalchemy.ext.declarative import DeclarativeMeta


from vantage6.common import STRING_ENCODING
from vantage6.common.serialization import log


def jsonable(value: list[DeclarativeMeta] | DeclarativeMeta) -> list | dict:
    """
    Convert a (list of) SQLAlchemy instance(s) to native Python objects.

    Parameters
    ----------
    value : list[DeclarativeMeta] | DeclarativeMeta
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

    elif isinstance(value, DeclarativeMeta):
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
