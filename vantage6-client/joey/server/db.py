# -*- coding: utf-8 -*-
import os
import logging
import datetime

import enum
import json

import sqlalchemy as sql

from .models import ( Base, User, Organization, Authenticatable, Node, Task, 
    Member, Result, Collaboration)


def jsonable(value):
    """Convert a (list of) SQLAlchemy instance(s) to native Python objects."""
    if isinstance(value, list):
        return [jsonable(i) for i in value]

    elif isinstance(value, Base):
        retval = dict()
        mapper = sql.inspect(value.__class__)

        columns = [c.key for c in mapper.columns if c.key not in value._hidden_attributes]

        for column in columns:
            column_value = getattr(value, column)

            if isinstance(column_value, enum.Enum):
                column_value = column_value.value
            elif isinstance(column_value, datetime.datetime):
                column_value = column_value.isoformat()

            retval[column] = column_value

        return retval

    # FIXME: does it make sense to raise an exception or should base types
    #        (or other JSON-serializable types) just be returned as-is?
    raise Exception('value should be instance of db.Base or list!')


def jsonify(value):
    """Convert a (list of) SQLAlchemy instance(s) to a JSON (string)."""
    return json.dumps(jsonable(value))


