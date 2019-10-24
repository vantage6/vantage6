import logging
import os 

from sqlalchemy import Column, Integer, inspect
from sqlalchemy.orm.session import Session, sessionmaker
from sqlalchemy.ext.declarative import declarative_base, declared_attr

from sqlalchemy import create_engine
from sqlalchemy.orm.session import Session
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.orm.exc import NoResultFound


from vantage.util import Singleton

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

class Database(metaclass=Singleton):

    def __init__(self):
        self.engine = None
        self.Session = None
        self.object_session = None

    def drop_all(self):
        Base.metadata.drop_all(self.engine)
        Base.metadata.create_all(bind=self.engine)


    def connect(self, URI='sqlite:////tmp/test.db', drop_all=False):
        
        self.URI = URI
        
        URL = make_url(URI)
        log.info("Initializing the database")
        log.debug("  driver:   {}".format(URL.drivername))
        log.debug("  host:     {}".format(URL.host))
        log.debug("  port:     {}".format(URL.port))
        log.debug("  database: {}".format(URL.database))
        log.debug("  username: {}".format(URL.username))

        # Make sure that the director for the file database exists.    
        if URL.host is None and URL.database:        
            os.makedirs(os.path.dirname(URL.database), exist_ok=True)

        self.engine = create_engine(URI, convert_unicode=True)
        self.Session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
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
    def get(cls, id_=None, with_session=False):
        
        session = Database().Session

        if id_ is None:
            result = session.query(cls).all()
        else:
            try:
                result = session.query(cls).filter_by(id=id_).one()
            except NoResultFound:
                result = None

        if with_session:
            return result, session

        return result

    def save(self):
        if self.id is None:
            session = Database().Session
            session.add(self)
        else:
            session = Database().object_session(self)
        session.commit()

    def delete(self):
        if not self.id:
            session = Database().Session
        else:
            session = Database().object_session(self)
        session.delete(self)
        session.commit()

    def update(self, include=None, exclude=None, **kwargs):
        """Update this instance using a dictionary."""

        # Get a list of attributes available to this class.
        # This should exclude relationships!
        inst = inspect(self)
        cols = [c_attr.key for c_attr in inst.mapper.column_attrs]
        cols = set(cols)

        # Cast the list of attributes we're trying to update to a set.
        keys = set(kwargs.keys())

        # Only *keep* keys listed in `include`
        if include:
            if type(include) != type([]):
                include = [include, ]
            include = set(include)
            keys = keys & include

        # Remove any keys that are in `exclude`
        if exclude:
            if type(exclude) != type([]):
                exclude = [exclude, ]
            exclude = set(exclude)
            keys = keys - exclude

        # Keep only those keys that are proper attributes
        attrs = cols.intersection(keys)
        for attr in attrs:
            setattr(self, attr, kwargs[attr])

Base = declarative_base(cls=ModelBase)
