from __future__ import annotations
from enum import Enum as Enumerate
from typing import Union

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
    """
    Table that describes which rules are available.

    A rule gives access to a single type of action with a given operation,
    scope and resource on which it acts.
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
    def get_by_(cls, name: str, scope: str, operation: str
                ) -> Union[Rule, None]:
        """
        Get a rule by its name, scope and operation.

        Parameters
        ----------
        name : str
            Name of the resource on which the rule acts, e.g. 'node'
        scope : str
            Scope of the rule, e.g. 'organization'
        operation : str
            Operation of the rule, e.g. 'view'

        Returns
        -------
        Rule or None
            Rule with the given name, scope and operation or None if no rule
            with the given name, scope and operation exists
        """
        session = DatabaseSessionManager.get_session()
        try:
            return session.query(cls).filter_by(
                name=name,
                operation=operation,
                scope=scope
            ).first()
        except NoResultFound:
            return None

    def __repr__(self) -> str:
        """
        String representation of the rule.

        Returns
        -------
        str
            String representation of the rule
        """
        return (
            f"<Rule "
            f"{self.id}: '{self.name}', "
            f"operation: {self.operation}, "
            f"scope: {self.scope}"
            ">"
        )
