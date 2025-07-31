# TODO this is almost a copy of the same file in the server package. Refactor
import inspect as class_inspect
import logging
import os
from time import sleep
from typing import Any

from flask.globals import g
from sqlalchemy import (
    Column,
    Integer,
    Table,
    create_engine,
    exists,
    inspect,
    select,
    text,
)
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import DeclarativeMeta, declared_attr
from sqlalchemy.orm import RelationshipProperty, scoped_session, sessionmaker
from sqlalchemy.orm.clsregistry import _ModuleMarker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.orm.session import Session

from vantage6.common import logger_name

from vantage6.backend.common import session
from vantage6.backend.common.globals import (
    MAX_NUMBER_OF_ATTEMPTS,
    RETRY_DELAY_IN_SECONDS,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class BaseDatabase:
    """
    Database class that is used to connect to the database and create the
    database session.

    The database is created as a singleton, so that it can be destroyed (as
    opposed to a module). This is especially useful when creating unit tests
    in which we want fresh databases every now and then.
    """

    def __init__(self):
        self.engine = None
        self.Session = None
        self.object_session = None
        self.allow_drop_all = False

    def _drop_all(self, base: DeclarativeMeta):
        """
        Drop all tables in the database.
        """
        if self.allow_drop_all:
            base.metadata.drop_all(bind=self.engine)
        else:
            log.error("Cannot drop tables, configuration does not allow this!")

    def _clear_data(
        self, base: DeclarativeMeta, db_session_mgr: type["BaseDatabaseSessionManager"]
    ):
        """
        Clear all data from the database.
        """
        meta = base.metadata
        session = db_session_mgr.get_session()
        for table in reversed(meta.sorted_tables):
            session.execute(table.delete())
        session.commit()
        db_session_mgr.clear_session()

    def _close(self, base: DeclarativeMeta):
        """
        Delete all tables and close the database connection. Only used for
        unit testing.
        """
        self._drop_all(base)
        if self.engine:
            self.engine.dispose()
        self.engine = None
        self.Session = None
        self.object_session = None
        self.allow_drop_all = False
        self.URI = None

    def _connect(
        self, base: DeclarativeMeta, uri="sqlite:////tmp/test.db", allow_drop_all=False
    ):
        """
        Connect to the database.

        Parameters
        ----------
        uri : str
            URI of the database. Defaults to a sqlite database in /tmp.
        allow_drop_all : bool, optional
            If True, the database can be dropped. Defaults to False.
        """
        self.allow_drop_all = allow_drop_all
        self.URI = uri

        max_time_in_minutes = int(
            (MAX_NUMBER_OF_ATTEMPTS * RETRY_DELAY_IN_SECONDS) / 60
        )

        URL = make_url(uri)
        log.info("Initializing the database")
        log.debug("  driver:   {}".format(URL.drivername))
        log.debug("  host:     {}".format(URL.host))
        log.debug("  port:     {}".format(URL.port))
        log.debug("  database: {}".format(URL.database))
        log.debug("  username: {}".format(URL.username))

        # Make sure that the director for the file database exists.
        if URL.host is None and URL.database:
            os.makedirs(os.path.dirname(URL.database), exist_ok=True)
        # Try connecting to the Db MAX_ATTEMPT times if not error occur
        for attempt in range(MAX_NUMBER_OF_ATTEMPTS):
            try:
                self.engine = create_engine(uri, pool_pre_ping=True)
                # we can call Session() to create a session, if a session already
                # exists it will return the same session (!). implicit access to the
                # Session (without calling it first). The scoped session is scoped to
                # the local thread the process is running in.
                self.session_a = scoped_session(
                    sessionmaker(autocommit=False, autoflush=False)
                )
                self.session_a.configure(bind=self.engine)

                # TODO BvB 7/2/2024 I think this session is not necessary as algorithm
                # store does not use iPython shell
                # because the Session factory returns the same session (if one exists
                # already) we need a second factory to create an alternative session.
                # this is required if we use both the flask session and the iPython.
                # Because the flask session is managed by the hooks `pre_request` and
                # `post request`. If we would use the same session for other tasks, the
                # session can be terminated unexpectedly.
                self.session_b = scoped_session(
                    sessionmaker(autocommit=False, autoflush=False)
                )
                self.session_b.configure(bind=self.engine)

                # short hand to obtain a object-session.
                self.object_session = Session.object_session

                base.metadata.create_all(bind=self.engine)
                break
            except OperationalError as e:
                log.error(f"Connection attempt failed: {str(e)}")

                # Check if the maximum retry duration has been exceeded
                if attempt < MAX_NUMBER_OF_ATTEMPTS - 1:
                    log.info(f"Retrying in {RETRY_DELAY_IN_SECONDS} seconds...")
                    sleep(RETRY_DELAY_IN_SECONDS)
                else:
                    raise Exception(
                        f"Unable to connect to the database!"
                        f" Timeout after {MAX_NUMBER_OF_ATTEMPTS} attempts and {max_time_in_minutes} minutes."
                        f" Please ensure the database is up and running."
                    ) from e

        log.info("Database initialized!")

        # add columns that are not yet in the database (they may have been
        # added in a newer minor version)
        self._add_missing_columns(base)

    def _add_missing_columns(self, base: DeclarativeMeta) -> None:
        """
        Check database tables to see if columns are missing that are described
        in the SQLAlchemy models, and add the missing columns
        """
        self.__iengine = inspect(self.engine)
        table_names = self.__iengine.get_table_names()

        # go through all SQLAlchemy models
        for table_cls in base.registry._class_registry.values():
            if isinstance(table_cls, _ModuleMarker):
                continue  # skip, not a model

            table_name = table_cls.__tablename__
            if table_name in table_names:
                non_existing_cols = self._get_non_existing_columns(
                    table_cls, table_name
                )

                for col in non_existing_cols:
                    self.add_col_to_table(col, table_cls)
            else:
                log.error(
                    f"Model {table_cls} declares table {table_name} which does"
                    " not exist in the database."
                )

    def _get_non_existing_columns(
        self, table_cls: Table, table_name: str
    ) -> list[Column]:
        """
        Return a list of columns that are defined in the SQLAlchemy model, but
        are not present in the database

        Parameters
        ----------
        table_cls: Table
            The table that is evaluated
        table_name: str
            The name of the table

        Returns
        -------
        list[Column]
            List of SQLAlchemy Column objects that are present in the model,
            but not in the database
        """
        column_names = [c["name"] for c in self.__iengine.get_columns(table_name)]
        mapper = inspect(table_cls)

        non_existing_columns = []
        for prop in mapper.attrs:
            if not isinstance(prop, RelationshipProperty):
                for column in prop.columns:
                    if self.is_column_missing(column, column_names, table_name):
                        non_existing_columns.append(column)

        return non_existing_columns

    def add_col_to_table(self, column: Column, table_cls: Table) -> None:
        """
        Database operation to add column to `Table`

        Parameters
        ----------
        column: Column
            The SQLAlchemy model column that is to be added
        table_cls: Table
            The SQLAlchemy table to which the column is to be added
        """
        col_name = column.key
        col_type = column.type.compile(self.engine.dialect)
        tab_name = table_cls.__tablename__
        log.warning(
            "Adding column '%s' to table '%s' as it did not exist yet",
            col_name,
            tab_name,
        )
        with self.engine.connect() as conn:
            with conn.begin():
                conn.execute(
                    text(
                        'ALTER TABLE "%s" ADD COLUMN %s %s'
                        % (tab_name, col_name, col_type)
                    )
                )

    @staticmethod
    def is_column_missing(
        column: Column, column_names: list[str], table_name: str
    ) -> bool:
        """Check if column is missing in the table

        Parameters
        ----------
        column: Column
            The column that is evaluated
        column_names: List[str]
            A list of all column names in the table
        table_name: str
            The name of the table the column resides in

        Returns
        -------
        boolean
            True if column is not in the table or a parent table
        """
        # the check for table_name is for columns that are actually not in
        # the current table but in the parent table, e.g. the column
        # 'status' in the user table is actually in the authenticatable table.
        return column.key not in column_names and str(column.table) == table_name


class BaseDatabaseSessionManager:
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
    def in_flask_request() -> bool:
        """
        Check if we are in a flask request.

        Returns
        -------
        boolean
            True if we are in a flask request, False otherwise
        """
        return True if g else False

    @staticmethod
    def _get_session(db_session_mgr: type["BaseDatabaseSessionManager"]) -> Session:
        """
        Get a session. Creates a new session if none exists.

        Parameters
        ----------
        db_session_mgr: type["BaseDatabaseSessionManager"]
            The database session manager - a derived class type of
            BaseDatabaseSessionManager

        Returns
        -------
        Session
            A database session
        """
        if db_session_mgr.in_flask_request():
            # needed for SocketIO requests
            if "session" not in g:
                db_session_mgr.new_session()

            return g.session
        else:
            if not session.session:
                db_session_mgr.new_session()

            return session.session

    @staticmethod
    def _new_session(
        db_session_mgr: type["BaseDatabaseSessionManager"],
        database: type["BaseDatabase"],
    ) -> None:
        """
        Create a new session. If we are in a flask request, the session is
        stored in the flask global `g`. Otherwise, the session is stored in
        the db module.

        Parameters
        ----------
        db_session_mgr: type["BaseDatabaseSessionManager"]
            The database session manager - a derived class type of
            BaseDatabaseSessionManager
        database: type["BaseDatabase"]
            The database class - a derived class type of BaseDatabase
        """
        if db_session_mgr.in_flask_request():
            g.session = database().session_a
        else:
            session.session = database().session_b

    @staticmethod
    def clear_session() -> None:
        """
        Clear the session. If we are in a flask request, the session is
        cleared from the flask global `g`. Otherwise, the session is removed
        from the db module.
        """
        if BaseDatabaseSessionManager.in_flask_request():
            # print(f"gsession: {g.session}")
            g.session.remove()
            # g.session = None
        else:
            if session.session:
                session.session.remove()
                session.session = None
            else:
                print("No DB session found to clear!")


class BaseModelBase:
    """
    Declarative base that defines default attributes. All data models inherit
    from this class.
    """

    _hidden_attributes = []

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # Primary key, internal use only
    id = Column(Integer, primary_key=True)

    @classmethod
    def _get(
        cls, db_session_mgr: type["BaseDatabaseSessionManager"], id_: int | None = None
    ):
        """
        Get a single object by its id, or a list of objects when no id is
        specified.

        Parameters
        ----------
        id_: int, optional
            The id of the object to get. If not specified, return all.
        """
        session_ = db_session_mgr.get_session()

        result = None

        stmt = select(cls)
        if id_ is None:
            result = session_.scalars(stmt).all()
        else:
            try:
                stmt = stmt.where(cls.id == id_)
                result = session_.scalars(stmt).one()
            except NoResultFound:
                result = None

        # Always commit to avoid that transaction is not ended in Postgres
        session_.commit()

        return result

    def _save(self, db_session_mgr: type["BaseDatabaseSessionManager"]) -> None:
        """
        Save the object to the database.

        Parameters
        ----------
        db_session_mgr: type["BaseDatabaseSessionManager"]
            The database session manager - a derived class type of
            BaseDatabaseSessionManager
        """
        session_ = db_session_mgr.get_session()

        # new objects do not have an `id`
        if not self.id:
            session_.add(self)

        session_.commit()

    def _delete(self, db_session_mgr: type["BaseDatabaseSessionManager"]) -> None:
        """
        Delete the object from the database.

        Parameters
        ----------
        db_session_mgr: type["BaseDatabaseSessionManager"]
            The database session manager - a derived class type of
            BaseDatabaseSession
        """
        session_ = db_session_mgr.get_session()

        session_.delete(self)
        session_.commit()

    @classmethod
    def _exists(
        cls, field: str, value: Any, db_session_mgr: type["BaseDatabaseSessionManager"]
    ) -> bool:
        """
        Check if a value exists for a given field in the database model.

        Parameters
        ----------
        field: str
            The field to check
        value: Any
            The value to check
        db_session_mgr: type["BaseDatabaseSessionManager"]
            The database session manager - a derived class type of
            BaseDatabaseSessionManager

        Returns
        -------
        bool
            True if the value exists, False otherwise
        """
        session_ = db_session_mgr.get_session()
        result = session_.scalar(select(exists().where(getattr(cls, field) == value)))
        session_.commit()
        return result

    @classmethod
    def help(cls) -> None:
        """
        Print a help message for the class.
        """
        i = inspect(cls)
        properties = "".join([f" ->{a.key}\n" for a in i.mapper.column_attrs])
        relations = "".join([f" ->{a[0]}\n" for a in i.relationships.items()])
        methods = class_inspect.getmembers(cls, predicate=class_inspect.isroutine)

        methods = "".join(
            [f" ->{key[0]}\n" for key in methods if not key[0].startswith("_")]
        )

        print(
            f"Table: {cls.__tablename__}\n\n"
            f"Properties: \n{properties}\n"
            f"Relations: \n{relations}\n"
            f"Methods: \n{methods}\n"
        )

    def __eq__(self, other: Any) -> bool:
        """
        Check if the object is equal to another object.

        Parameters
        ----------
        other: Any
            The other object to compare to

        Returns
        -------
        bool
            True if the objects are equal, False otherwise
        """
        return self.id == other.id

    def __hash__(self) -> int:
        """
        Hash the object.
        """
        return self.id
