# -*- coding: utf-8 -*-
import logging
import datetime

import enum
import json
import sqlalchemy as sql

# TODO this file is akward...
from vantage6.server.model import (
    Base,
    Task,
    Result,
    Organization,
    User,
    Node,
    Authenticatable,
    Collaboration,
    Member,
    Permission,
    Role,
    Rule,
    UserPermission,
    role_rule_association,
    AlgorithmPort
)
from vantage6.common import logger_name
from vantage6.common.globals import STRING_ENCODING


module_name = logger_name(__name__)
log = logging.getLogger(module_name)

# DB connection session. This is used by the iPython shell (from db import
# session). It is important to mention that the flask requests obtain their
# session from `g.session` which is initialized on `pre_request`.
session = None


def jsonable(value):
    """Convert a (list of) SQLAlchemy instance(s) to native Python objects."""
    if isinstance(value, list):
        return [jsonable(i) for i in value]

    elif isinstance(value, Base):
        log.debug(f"preparing={value}")
        retval = dict()
        mapper = sql.inspect(value.__class__)

        columns = [c.key for c in mapper.columns
                   if c.key not in value._hidden_attributes]

        for column in columns:
            # log.debug(f"processing column={column}")
            column_value = getattr(value, column)

            if isinstance(column_value, enum.Enum):
                column_value = column_value.value
            elif isinstance(column_value, datetime.datetime):
                column_value = column_value.isoformat()
            elif isinstance(column_value, bytes):
                log.debug(f"decoding bytes!")
                column_value = column_value.decode(STRING_ENCODING)

            retval[column] = column_value

        return retval

    # FIXME: does it make sense to raise an exception or should base types
    #        (or other JSON-serializable types) just be returned as-is?
    raise Exception('value should be instance of db.Base or list!')


def jsonify(value):
    """Convert a (list of) SQLAlchemy instance(s) to a JSON (string)."""
    return json.dumps(jsonable(value))
