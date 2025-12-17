"""
Database connection classes for the server.

Note that this file is almost identical to the one for the algorithm store. However,
this is necessary because the database class is a singleton so we have to create
two different classes for it.
"""

import logging
from typing import Any

from sqlalchemy.orm import declarative_base
from sqlalchemy.orm.session import Session

from vantage6.common import Singleton, logger_name

from vantage6.backend.common.base import (
    BaseDatabase,
    BaseDatabaseSessionManager,
    BaseModelBase,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Database(BaseDatabase, metaclass=Singleton):
    """
    Database class that is used to connect to the database and create the
    database session.

    The database is created as a singleton, so that it can be destroyed (as
    opposed to a module). This is especially useful when creating unit tests
    in which we want fresh databases every now and then.
    """

    def drop_all(self):
        """
        Drop all tables in the database.
        """
        self._drop_all(Base)

    def clear_data(self):
        """
        Clear all data from the database.
        """
        self._clear_data(Base, DatabaseSessionManager)

    def close(self):
        """
        Delete all tables and close the database connection. Only used for
        unit testing.
        """
        self._close(Base)

    def connect(self, uri="sqlite:////tmp/test.db", allow_drop_all=False):
        """
        Connect to the database.

        Parameters
        ----------
        uri : str
            URI of the database. Defaults to a sqlite database in /tmp.
        allow_drop_all : bool, optional
            If True, the database can be dropped. Defaults to False. Typically, it is
            only set to True for unit tests.
        """
        self._connect(Base, uri, allow_drop_all)


class DatabaseSessionManager(BaseDatabaseSessionManager):
    """
    Class to manage DB sessions.

    There are 2 different ways a session can be obtained. Either a session used
    within a request or a session used elsewhere (e.g. socketIO event, iPython
    or within the application itself).

    In case of the Flask request, the session is stored in the flask global
    `g`. Then, it can be accessed in every endpoint.

    In all other cases the session is attached to the db module.
    """

    @staticmethod
    def get_session() -> Session:
        """
        Get a session. Creates a new session if none exists.

        Returns
        -------
        Session
            A database session
        """
        return BaseDatabaseSessionManager._get_session(DatabaseSessionManager)

    @staticmethod
    def new_session() -> None:
        """
        Create a new session. If we are in a flask request, the session is
        stored in the flask global `g`. Otherwise, the session is stored in
        the db module.
        """
        BaseDatabaseSessionManager._new_session(DatabaseSessionManager, Database)


class ModelBase(BaseModelBase):
    """
    Declarative base that defines default attributes. All data models inherit
    from this class.
    """

    @classmethod
    def get(cls, id_: int = None):
        """
        Get a single object by its id, or a list of objects when no id is
        specified.

        Parameters
        ----------
        id_: int, optional
            The id of the object to get. If not specified, return all.
        """
        return cls._get(DatabaseSessionManager, id_)

    def save(self) -> None:
        """
        Save the object to the database.
        """
        return self._save(DatabaseSessionManager)

    def delete(self) -> None:
        """
        Delete the object from the database.
        """
        return self._delete(DatabaseSessionManager)

    @classmethod
    def exists(cls, field: str, value: Any) -> bool:
        """
        Check if a value exists for a given field in the database model.

        Parameters
        ----------
        field: str
            The field to check
        value: Any
            The value to check

        Returns
        -------
        bool
            True if the value exists, False otherwise
        """
        return cls._exists(field, value, DatabaseSessionManager)


Base = declarative_base(cls=ModelBase)
