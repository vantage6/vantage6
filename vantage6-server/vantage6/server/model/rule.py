from __future__ import annotations

from sqlalchemy import Column, String, Text, select
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common.enum import StrEnumBase

from vantage6.server.model.base import Base, DatabaseSessionManager


class Operation(StrEnumBase):
    """Enumerator of all available operations"""

    VIEW = "view"
    EDIT = "edit"
    CREATE = "create"
    DELETE = "delete"
    SEND = "send"
    RECEIVE = "receive"


class Scope(StrEnumBase):
    """Enumerator of all available scopes"""

    OWN = "own"
    ORGANIZATION = "organization"
    COLLABORATION = "collaboration"
    GLOBAL = "global"

    @classmethod
    def get_name_from_value(cls, value: str) -> str | None:
        """
        Get the name of a scope from its value.

        This is used to generate the full names for API output.

        Parameters
        ----------
        value : str
            Value of the scope

        Returns
        -------
        str | None
            Name of the scope or None if no scope with the given value exists
        """
        return next((scope.name.lower() for scope in cls if scope == value), None)

    def __lt__(self, other: Scope) -> bool:
        """
        Check if this scope is strictly lower than another scope.
        """
        if self == Scope.OWN and other != Scope.OWN:
            return True
        elif self == Scope.ORGANIZATION and other in [
            Scope.COLLABORATION,
            Scope.GLOBAL,
        ]:
            return True
        elif self == Scope.COLLABORATION and other == Scope.GLOBAL:
            return True
        return False

    def __le__(self, other: Scope) -> bool:
        """
        Check if this scope is lower or equal to another scope.
        """
        return self == other or self < other

    def __gt__(self, other: Scope) -> bool:
        """
        Check if this scope is strictly greater than another scope.
        """
        return not self <= other

    def __ge__(self, other: Scope) -> bool:
        """
        Check if this scope is greater or equal to another scope.
        """
        return not self < other


class Rule(Base):
    """Rules to determine permissions in an API endpoint.

    A rule gives access to a single type of action with a given operation, scope and
    resource on which it acts. Note that rules are defined on startup of the server,
    based on permissions defined in the endpoints. You cannot edit the rules in the
    database.

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

    Relationships
    -------------
    roles : list[:class:`.~vantage6.server.model.role.Role`]
        Roles that have this rule
    users : list[:class:`.~vantage6.server.model.user.User`]
        Users that have this rule
    """

    # fields
    name = Column(Text)
    operation = Column(String)
    scope = Column(String)
    description = Column(String)

    # relationships
    roles = relationship(
        "Role", back_populates="rules", secondary="role_rule_association"
    )
    users = relationship("User", back_populates="rules", secondary="UserPermission")

    @classmethod
    def get_by_(cls, name: str, scope: Scope, operation: Operation) -> Rule | None:
        """
        Get a rule by its name, scope and operation.

        Parameters
        ----------
        name : str
            Name of the resource on which the rule acts, e.g. 'node'
        scope : Scope
            Scope of the rule, e.g. 'organization'
        operation : Operation
            Operation of the rule, e.g. 'view'

        Returns
        -------
        Rule | None
            Rule with the given name, scope and operation or None if no rule
            with the given name, scope and operation exists
        """
        session = DatabaseSessionManager.get_session()
        try:
            stmt = select(cls).filter_by(
                name=name, scope=scope.value, operation=operation.value
            )
            result = session.scalars(stmt).first()
            session.commit()
            return result
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
