# -*- coding: utf-8 -*-
import os
import logging
import datetime

import enum
import json
import bcrypt

from sqlalchemy import *
from sqlalchemy import func
from sqlalchemy.sql import exists
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.orm.session import Session
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm.exc import NoResultFound

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

# ------------------------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------------------------
def init(URI='sqlite:////tmp/test.db', drop_all=False):
    """Initialize the database."""
    module_name = __name__.split('.')[-1]
    log = logging.getLogger(module_name)

    url = make_url(URI)
    log.info("Initializing the database")
    log.debug("  driver:   {}".format(url.drivername))
    log.debug("  host:     {}".format(url.host))
    log.debug("  port:     {}".format(url.port))
    log.debug("  database: {}".format(url.database))
    log.debug("  username: {}".format(url.username))

    # TODO is this really necessary
    from . import db
    db.URI = URI

    # Make sure that the director for the file database exists.
    URL = make_url(URI)
    if URL.host is None and URL.database:        
        os.makedirs(os.path.dirname(URL.database), exist_ok=True)

    db.engine = create_engine(URI, convert_unicode=True)
    db.Session = scoped_session(sessionmaker(autocommit=False, autoflush=False))
    db.object_session = Session.object_session

    Session.configure(bind=db.engine)

    if drop_all:
        log.warn("Dropping existing tables!")
        Base.metadata.drop_all(db.engine)

    Base.metadata.create_all(bind=db.engine)
    log.info("Database initialized!")


def jsonable(value):
    """Convert a (list of) SQLAlchemy instance(s) to native Python objects."""
    if isinstance(value, list):
        return [jsonable(i) for i in value]

    elif isinstance(value, Base):
        retval = dict()
        mapper = inspect(value.__class__)

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


# ------------------------------------------------------------------------------
# Base declaration.
# ------------------------------------------------------------------------------
class Base(object):
    """Declarative base that defines default attributes."""
    _hidden_attributes = []

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()
    
    # Primay key, internal use only
    id = Column(Integer, primary_key=True)

    @classmethod
    def get(cls, id_=None, with_session=False):
        session = Session()

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
            session = Session()
            session.add(self)
        else:
            session = Session.object_session(self)

        session.commit()

    def delete(self):
        if not self.id:
            session = Session()
        else:
            session = Session.object_session(self)

        session.delete(self)
        session.commit()


Base = declarative_base(cls=Base)


# ------------------------------------------------------------------------------
# Real model/table definitions start here.
# ------------------------------------------------------------------------------
association_table_organization_collaboration = Table(
    'association_table_organization_collaboration', 
    Base.metadata,
    Column('organization_id', Integer, ForeignKey('organization.id')),
    Column('collaboration_id', Integer, ForeignKey('collaboration.id'))
)


# ------------------------------------------------------------------------------
class Organization(Base):
    """A legal entity."""
    name = Column(String)
    domain = Column(String)
    address1 = Column(String)
    address2 = Column(String)
    zipcode = Column(String)
    country = Column(String)


# ------------------------------------------------------------------------------
class Collaboration(Base):
    """Combination of 2 or more Organizations."""

    name = Column(String)

    organizations = relationship(
        'Organization', 
        secondary=association_table_organization_collaboration, 
        backref='collaborations'
    )

    def get_organization_ids(self):
        return [organization.id for organization in self.organizations]

    def get_task_ids(self):
        return [task.id for task in self.tasks]

    @classmethod
    def get_collaboration_by_name(cls, name):
        session = Session()
        try:
            return session.query(cls).filter_by(name=name).one()
        except NoResultFound:
            return None


# ------------------------------------------------------------------------------
class Authenticatable(Base):
    """Yes, there is a typo in this class' name ;-)"""

    type = Column(String(50))
    ip = Column(String)
    last_seen = Column(DateTime)
    status = Column(String)


    __mapper_args__ = {
        'polymorphic_identity':'authenticatable',
        'polymorphic_on': type,
    }


# ------------------------------------------------------------------------------
class User(Authenticatable):
    """User (person) that can access the system."""
    _hidden_attributes = ['password_hash']

    id = Column(Integer, ForeignKey('authenticatable.id'), primary_key=True)

    username = Column(String)    
    password_hash = Column(String)
    firstname = Column(String)
    lastname = Column(String)
    roles = Column(String)

    organization_id = Column(Integer, ForeignKey('organization.id'))
    organization = relationship('Organization', backref='users')

    __mapper_args__ = {
        'polymorphic_identity':'user',
    }

    # TODO init method not required
    def __init__(self, username=None, password='password',
                 firstname=None, lastname=None, organization_id=None, roles='Administrator'):
        self.username = username
        self.set_password(password)
        self.firstname = firstname
        self.lastname = lastname
        self.roles = roles
        self.organization_id = organization_id

    # Copied from https://docs.pylonsproject.org/projects/pyramid/en/master/tutorials/wiki2/definingmodels.html
    def set_password(self, pw):
        pwhash = bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt())
        self.password_hash = pwhash.decode('utf8')

    # Copied from https://docs.pylonsproject.org/projects/pyramid/en/master/tutorials/wiki2/definingmodels.html
    def check_password(self, pw):
        if self.password_hash is not None:
            expected_hash = self.password_hash.encode('utf8')
            return bcrypt.checkpw(pw.encode('utf8'), expected_hash)
        return False

    @classmethod
    def getByUsername(cls, username):
        session = Session()
        return session.query(cls).filter_by(username=username).one()

    @classmethod
    def get_user_list(cls, filters=None):
        session = Session()
        return session.query(cls).all()

    @classmethod
    def username_exists(cls, username):
        session = Session()
        res = session.query(exists().where(cls.username == username)).scalar()
        return res


# ------------------------------------------------------------------------------
class Node(Authenticatable):
    """Application that executes Tasks."""
    _hidden_attributes = ['api_key']

    id = Column(Integer, ForeignKey('authenticatable.id'), primary_key=True)
    
    name = Column(String)
    api_key = Column(String)

    collaboration_id = Column(Integer, ForeignKey('collaboration.id'))
    collaboration = relationship('Collaboration', backref='nodes')

    organization_id = Column(Integer, ForeignKey('organization.id'))
    organization = relationship('Organization', backref='nodes')

    __mapper_args__ = {
        'polymorphic_identity': 'node',
    }

    @property
    def open_tasks(self):
        # return [result for result in self.taskresults if result.finished_at is None]
        # print(self.taskresults, type(self.taskresults))

        values = list()
        for r in self.taskresults:
            values.append(r)

        return values

    @classmethod
    def get_by_api_key(cls, api_key):
        """returns Node based on the provided API key"""
        session = Session()

        try:
            return session.query(cls).filter_by(api_key=api_key).one()
        except NoResultFound:
            return None


# ------------------------------------------------------------------------------
class Task(Base):
    """Central definition of a single task."""
    name = Column(String)
    description = Column(String)
    image = Column(String)
    input = Column(Text)

    run_id = Column(Integer) # multiple tasks can belong to a single run
    parent_task_id = Column(Integer) # a task can be a subtask 

    collaboration_id = Column(Integer, ForeignKey('collaboration.id'))
    collaboration = relationship('Collaboration', backref='tasks')


    @hybrid_property
    def complete(self):
        return all([r.finished_at for r in self.results])

    @classmethod
    def next_run_id(cls):
        session = Session()
        max_run_id = session.query(func.max(cls.run_id)).scalar()
        if not max_run_id:
            return 1
        else:
            return max_run_id + 1


# ------------------------------------------------------------------------------
class TaskResult(Base):
    """Result of a Task as executed by a Node.

    Unfinished TaskResults constitute a Node's todo list.
    """
    result = Column(Text)

    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log = Column(Text)

    task_id = Column(Integer, ForeignKey('task.id'))
    task = relationship('Task', backref='results')

    node_id = Column(Integer, ForeignKey('node.id'))
    node = relationship('Node', backref='taskresults')

    # collaboration_id = Column(Integer, ForeignKey('collaboration.id'))
    # collaboration = relationship('Collaboration', backref='taskresults')

    @hybrid_property
    def isComplete(self):
        return self.finished_at is not None







