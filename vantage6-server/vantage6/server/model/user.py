import bcrypt

from sqlalchemy import Column, String, Integer, ForeignKey, exists
from sqlalchemy.orm import relationship

from .base import Database
from .authenticable import Authenticatable


class User(Authenticatable):
    """User (person) that can access the system.

    Users always belong to an organization and can have certain
    rights within an organization.
    """
    _hidden_attributes = ['password']

    # overwrite id with linked id to the authenticatable
    id = Column(Integer, ForeignKey('authenticatable.id'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity':'user',
    }

    # fields
    username = Column(String, unique=True)
    password = Column(String)
    firstname = Column(String)
    lastname = Column(String)
    roles = Column(String)
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    organization = relationship("Organization", back_populates="users")

    def __repr__(self):
        organization = self.organization.name if self.organization else "None"
        return (
            f"<User "
            f"id={self.id}, username='{self.username}', roles='{self.roles}', "
            f"organization='{organization}'"
            f">"
        )

    def set_password(self, pw):
        pwhash = bcrypt.hashpw(pw.encode('utf8'), bcrypt.gensalt())
        self.password = pwhash.decode('utf8')

    def check_password(self, pw):
        if self.password is not None:
            expected_hash = self.password.encode('utf8')
            return bcrypt.checkpw(pw.encode('utf8'), expected_hash)
        return False

    @classmethod
    def getByUsername(cls, username):
        session = Database().Session
        return session.query(cls).filter_by(username=username).one()

    @classmethod
    def get_user_list(cls, filters=None):
        session = Database().Session
        return session.query(cls).all()

    @classmethod
    def username_exists(cls, username):
        session = Database().Session
        return session.query(exists().where(cls.username == username)).scalar()
