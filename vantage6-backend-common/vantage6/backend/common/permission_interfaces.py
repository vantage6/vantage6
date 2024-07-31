from __future__ import annotations

from typing import Any

from sqlalchemy.orm.exc import NoResultFound

from vantage6.backend.common.base import DatabaseSessionManager


class RuleInterface:
    name: Any
    operation: Any
    description: Any

    @classmethod
    def get_by_(cls, *args, **kwargs):
        raise NotImplemented("get_by_ method must be implemented for Rule class")

    def __repr__(self) -> str:
        """
        String representation of the rule.

        Returns
        -------
        str
            String representation of the rule
        """
        raise NotImplemented("__repr__ method must be implemented for Rule class")


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
        raise NotImplemented("__repr__ method must be implemented for Role class")
