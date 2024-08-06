from __future__ import annotations

from typing import Any

from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import Column, Integer, ForeignKey, Table

from vantage6.backend.common.base import Base, DatabaseSessionManager

role_rule_association = Table(
    "role_rule_association",
    Base.metadata,
    Column("role_id", Integer, ForeignKey("role.id")),
    Column("rule_id", Integer, ForeignKey("rule.id")),
)


class RuleInterface:
    name: Any
    operation: Any
    description: Any

    @classmethod
    def get_by_(cls, *args, **kwargs):
        raise NotImplementedError("get_by_ method must be implemented for Rule class")

    def __repr__(self) -> str:
        """
        String representation of the rule.

        Returns
        -------
        str
            String representation of the rule
        """
        raise NotImplementedError("__repr__ method must be implemented for Rule class")


class RoleInterface:
    name: Any
    description: Any
    rules: Any
    users: Any

    @classmethod
    def get_by_name(cls, name: str):
        session = DatabaseSessionManager.get_session()
        try:
            result = session.query(cls).filter_by(name=name).first()
            session.commit()
            return result
        except NoResultFound:
            return None

    def __repr__(self) -> str:
        """
        String representation of the role.

        Returns
        -------
        str
            String representation of the role
        """
        raise NotImplementedError("__repr__ method must be implemented for Role class")
