
from enum import Enum as Enumerate

from sqlalchemy import Column, Text, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from vantage6.server.model.base import Base, Database

from vantage6.server.model import Base


class Operation(Enumerate):
    VIEW = 0
    EDIT = 1
    CREATE = 2
    DELETE = 3


class Scope(Enumerate):
    OWN = 0
    ORGANIZATION = 1
    COLLABORATION = 2
    GLOBAL = 3


class Rule(Base):
    """Rules to determine permissions in an API endpoint.
    """

    # fields
    name = Column(Text)
    operation = Column(Enum(Operation))
    scope = Column(Enum(Scope))
    description = Column(String)

    # relationships
    roles = relationship("Role", back_populates="rules",
                         secondary="role_rule_association")
    users = relationship("User", back_populates="rules",
                         secondary="UserPermission")

    @classmethod
    def get_by_name(cls, name):
        session = Database().Session
        try:
            return session.query(cls).filter_by(name=name).first()
        except NoResultFound:
            return None

    def __repr__(self):
        return (
            f"<Rule {self.id}, "
            f"name: {self.name}, "
            f"operation: {self.operation}, "
            f"scope: {self.scope}"
            ">"
        )
