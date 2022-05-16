import logging
import os
import inspect as class_inspect
from flask.globals import g

from sqlalchemy import Column, Integer, inspect
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common import logger_name, Singleton
from vantage6.server import db


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Database(metaclass=Singleton):
    """A singleton we can destroy, a module we cannot.

        Thats why we want a singlton. This is especially usefull when creating
        unit test in which we want fresh databases every now and then.
    """

    def __init__(self):
        self.engine = None
        self.Session = None
        self.object_session = None
        self.allow_drop_all = False

    def drop_all(self):
        if self.allow_drop_all:
            Base.metadata.drop_all(bind=self.engine)
            # Base.metadata.create_all(bind=self.engine)
            # self.Session.close()
        else:
            log.error("Cannot drop tables, configuration does not allow this!")

    def clear_data(self):
        meta = Base.metadata
        session = DatabaseSessionManager.get_session()
        for table in reversed(meta.sorted_tables):
            session.execute(table.delete())
        session.commit()
        DatabaseSessionManager.clear_session()

    def close(self):
        self.drop_all()
        self.engine = None
        self.Session = None
        self.object_session = None
        self.allow_drop_all = False
        self.URI = None

    def connect(self, uri='sqlite:////tmp/test.db', allow_drop_all=False):

        self.allow_drop_all = allow_drop_all
        self.URI = uri

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

        self.engine = create_engine(uri, convert_unicode=True,
                                    pool_pre_ping=True)

        # we can call Session() to create a session, if a session already
        # exists it will return the same session (!). implicit access to the
        # Session (without calling it first). The scoped session is scoped to
        # the local thread the process is running in.
        self.session_a = scoped_session(sessionmaker(autocommit=False,
                                                     autoflush=False))
        self.session_a.configure(bind=self.engine)

        # because the Session factory returns the same session (if one exists
        # already) we need a second factory to create an alternative session.
        # this is required if we use both the flask session and the iPython.
        # Because the flask session is managed by the hooks `pre_request` and
        # `post request`. If we would use the same session for other tasks, the
        # session can be terminated unexpectedly.
        self.session_b = scoped_session(sessionmaker(autocommit=False,
                                                     autoflush=False))
        self.session_b.configure(bind=self.engine)

        # short hand to obtain a object-session.
        self.object_session = Session.object_session

        Base.metadata.create_all(bind=self.engine)
        log.info("Database initialized!")


class DatabaseSessionManager:
    """Class to manage DB sessions from.

    There are 2 different ways a session can be obtained. Either a session used
    within a request or a session used else where (e.g. iPython or within the
    application itself).

    In case of the flask-request the session is stored in the flask global `g`.
    So that it can be accessed in every endpoint.

    In all other cases the session is attached to the db module.
    """

    @staticmethod
    def in_flask_request():
        return True if g else False

    @staticmethod
    def get_session():
        if DatabaseSessionManager.in_flask_request():

            # needed for SocketIO requests
            if 'session' not in g:
                DatabaseSessionManager.new_session()

            return g.session
        else:
            # log.critical('Obtaining non flask session')
            if not db.session:
                DatabaseSessionManager.new_session()
                # log.critical('WE NEED TO MAKE A NEW ONE')

            # print(f'db.session {db.session}')
            return db.session

    @staticmethod
    def new_session():
        # log.critical('Create new DB session')
        if DatabaseSessionManager.in_flask_request():

            g.session = Database().session_a

            # g.session.refresh()
            # print('new flask session')
        else:
            db.session = Database().session_b

    @staticmethod
    def clear_session():
        if DatabaseSessionManager.in_flask_request():
            # print(f"gsession: {g.session}")
            g.session.remove()
            # g.session = None
        else:
            if db.session:
                db.session.remove()
                db.session = None
            else:
                print('No DB session found to clear!')


class ModelBase:
    """Declarative base that defines default attributes."""
    _hidden_attributes = []

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # Primary key, internal use only
    id = Column(Integer, primary_key=True)

    @classmethod
    def get(cls, id_=None):

        session = DatabaseSessionManager.get_session()

        result = None

        if id_ is None:
            result = session.query(cls).all()
        else:
            try:
                result = session.query(cls).filter_by(id=id_).one()
            except NoResultFound:
                result = None

        return result

    def save(self) -> None:

        session = DatabaseSessionManager.get_session()

        # new objects do not have an `id`
        if not self.id:
            session.add(self)

        session.commit()

    def delete(self) -> None:

        session = DatabaseSessionManager.get_session()

        session.delete(self)
        session.commit()

    @classmethod
    def help(cls) -> str:
        i = inspect(cls)
        properties = ''.join([f' ->{a.key}\n' for a in i.mapper.column_attrs])
        relations = ''.join([f' ->{a[0]}\n' for a in i.relationships.items()])
        methods = class_inspect.getmembers(cls,
                                           predicate=class_inspect.isroutine)

        methods = ''.join([f' ->{key[0]}\n' for key in methods
                          if not key[0].startswith('_')])

        print(
            f'Table: {cls.__tablename__}\n\n'
            f'Properties: \n{properties}\n'
            f'Relations: \n{relations}\n'
            f'Methods: \n{methods}\n'
        )


Base = declarative_base(cls=ModelBase)
