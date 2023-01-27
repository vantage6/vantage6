
from enum import Enum as Enumerate

from sqlalchemy import Column, Text, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound
from vantage6.server.model.base import Base, DatabaseSessionManager


class Operation(Enumerate):
    """ Enumerator of all available operations """
    VIEW = "v"
    EDIT = "e"
    CREATE = "c"
    DELETE = "d"


class Scope(Enumerate):
    """ Enumerator of all available scopes """
    OWN = "own"
    ORGANIZATION = "org"
    COLLABORATION = "col"
    GLOBAL = "glo"


class Rule(Base):
    """Rules to determine permissions in an API endpoint.

    Attributes
    ----------
    name : str
        Name of the rule
    operation : Operation
        Operation of the rule
    scope : Scope
        Scope of the rule
    description : str
        Description of the rule
    roles : list[Role]
        Roles that have this rule
    users : list[User]
        Users that have this rule
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
    def get_by_(cls, name: str, scope: str, operation: str):
        session = DatabaseSessionManager.get_session()
        try:
            return session.query(cls).filter_by(
                name=name,
                operation=operation,
                scope=scope
            ).first()
        except NoResultFound:
            return None

    def __repr__(self):
        return (
            f"<Rule "
            f"{self.id}: '{self.name}', "
            f"operation: {self.operation}, "
            f"scope: {self.scope}"
            ">"
        )
