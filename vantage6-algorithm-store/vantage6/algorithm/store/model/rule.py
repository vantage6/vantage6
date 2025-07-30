from __future__ import annotations

from sqlalchemy import Column, String, Text, select
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common.enum import EnumBase

from vantage6.backend.common.permission_models import RuleInterface

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager


class Operation(EnumBase):
    """Enumerator of all available operations"""

    VIEW = "view"
    EDIT = "edit"
    CREATE = "create"
    DELETE = "delete"


class Rule(Base, RuleInterface):
    """Rules to determine permissions in an API endpoint.

    A rule gives access to a single type of action with a given operation
    and resource on which it acts. Note that rules are defined on startup
    of the server, based on permissions defined in the endpoints. You cannot
    edit the rules in the database.

    Attributes
    ----------
    name : str
        Name of the rule
    operation : Operation
        Operation of the rule
    description : str
        Description of the rule
    roles : list[:class:`.~vantage6.algorithm.store.model.role.Role`]
        Roles that have this rule
    """

    # fields
    name = Column(Text)
    operation = Column(String)
    description = Column(String)

    # relationships
    roles = relationship(
        "Role", back_populates="rules", secondary="role_rule_association"
    )
    users = relationship("User", back_populates="rules", secondary="UserPermission")

    @classmethod
    def get_by_(cls, name: str, operation: str) -> Rule | None:
        """
        Get a rule by its name and operation.

        Parameters
        ----------
        name : str
            Name of the resource on which the rule acts, e.g. 'algorithm'
        operation : str
            Operation of the rule, e.g. 'view'

        Returns
        -------
        Rule | None
            Rule with the given name and operation or None if no rule
            with the given name, scope and operation exists
        """
        session = DatabaseSessionManager.get_session()
        try:
            result = session.scalars(
                select(cls).filter_by(
                    name=name,
                    operation=operation,
                )
            ).first()
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
        return f"<Rule {self.id}: '{self.name}', operation: {self.operation}>"
