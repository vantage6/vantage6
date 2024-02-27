# TODO this is almost a copy of the same file in the server package. Refactor
# TODO this file is awkward...
import logging
import datetime

import enum
import sqlalchemy as sql

# Note: by importing these classes, the classes are registered in the Base's
# SQLAlchemy metadata. This is required for SQLAlchemy to be able to map the
# classes to the database tables, and e.g. initialize the database tables on
# startup.
from vantage6.algorithm.store.model import (
    Base,
    Algorithm,
    Argument,
    Database,
    Function,
    Permission,
    Role,
    Rule,
    User,
    Review,
    Vantage6Server,
)
from vantage6.common import logger_name
from vantage6.common.globals import STRING_ENCODING


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


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
            # log.debug(f"processing column={column}")
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
