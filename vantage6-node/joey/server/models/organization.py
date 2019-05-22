from sqlalchemy import Column, String
from sqlalchemy.orm import Session, relationship
from sqlalchemy.orm.exc import NoResultFound

from .base import Base, Database
from .member import Member
from .collaboration import Collaboration
from .user import User


class Organization(Base):
    """A legal entity.
    
    An organization plays a central role in managing distributed tasks. Each
    Organization contains a public key which other organizations can use to 
    send encrypted messages that only this organization can read.
    """

    # fields
    name = Column(String)
    domain = Column(String)
    address1 = Column(String)
    address2 = Column(String)
    zipcode = Column(String)
    country = Column(String)
    public_key = Column(String)

    # relations
    collaborations = relationship("Collaboration", secondary="Member",
        back_populates="organizations")
    task_assignments = relationship("TaskAssignment", 
        back_populates="organization")
    nodes = relationship("Node", back_populates="organization")
    users = relationship("User", back_populates="organization")

    @classmethod
    def get_by_name(cls, name):
        session = Database().Session
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    def __repr__(self):
        number_of_users = len(self.users)
        return ("<Organization "
            f"name:{self.name}, "
            f"domain:{self.domain}, "
            f"users:{number_of_users}"
        ">")
