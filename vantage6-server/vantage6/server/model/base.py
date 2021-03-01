import logging
import os

from sqlalchemy import Column, Integer, inspect
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.util.langhelpers import NoneType

from vantage6.common import logger_name, Singleton


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

        self.engine = create_engine(uri, convert_unicode=True)

        # we can call Session() to create a new unique session
        # (self.Session is a session factory). Its also possible to use
        # implicit access to the Session (without calling it first). The
        # scoped session is scoped to the local thread the process is running
        # in.
        self.Session = scoped_session(sessionmaker(autocommit=False,
                                                   autoflush=False))

         # short hand to obtain a object-session.
        self.object_session = Session.object_session

        self.Session.configure(bind=self.engine)

        Base.metadata.create_all(bind=self.engine)
        log.info("Database initialized!")


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

        session = Database().Session
        # session.begin()
        result = None
        try:
            if id_ is None:
                result = session.query(cls).all()
            else:
                try:
                    result = session.query(cls).filter_by(id=id_).one()
                except NoResultFound:
                    result = None
        except InvalidRequestError as e:
            log.warning('Exception on getting!')
            log.debug(e)
            # session.invalidate()
            session.rollback()
        # finally:
        #     session.close()

        return result

    def save(self):

        # new objects do not have an `id`
        session = Database().object_session(self) if self.id else \
            Database().Session
        # session.begin()
        try:
            if not self.id:
                session.add(self)
            session.commit()

        except InvalidRequestError as e:
            log.error("Exception when saving!")
            log.debug(e)
            # session.invalidate()
            session.rollback()

        # finally:
        #     session.close()


    def delete(self):
        session = Database().object_session(self) if self.id else \
            Database().Session

        # session.begin()

        try:
            session.delete(self)
            session.commit()

        except InvalidRequestError as e:
            log.info("Exception when deleting!")
            log.debug(e)
            # session.invalidate()
            session.rollback()

        # finally:
        #     session.close()

Base = declarative_base(cls=ModelBase)
