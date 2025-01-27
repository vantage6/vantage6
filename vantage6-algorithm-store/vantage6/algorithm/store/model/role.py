from __future__ import annotations
from sqlalchemy import Column, Text, select
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.backend.common.permission_models import RoleInterface
from vantage6.common import logger_name

import logging

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Role(Base, RoleInterface):
    """Collection of :class:`.~vantage6.algorithm.store.model.rule.Role` permissions

    Attributes
    ----------
    name : str
        Name of the role
    description : str
        Description of the role
    rules : list[:class:`.~vantage6.algorithm.store.model.rule.Rule`]
        List of rules that belong to this role
    users : list[:class:`.~vantage6.algorithm.store.model.user.User`]
        List of users that belong to this role
    """

    # fields
    name = Column(Text)
    description = Column(Text)

    # relationships
    rules = relationship(
        "Rule", back_populates="roles", secondary="role_rule_association"
    )

    users = relationship("User", back_populates="roles", secondary="Permission")

    @classmethod
    def get_by_name(cls, name: str):
        session = DatabaseSessionManager.get_session()
        try:
            result = session.scalars(select(cls).filter_by(name=name)).first()
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
        return (
            f"<Role "
            f"{self.id}: '{self.name}', "
            f"description: {self.description}, "
            # f"{len(self.users)} user(s)"
            ">"
        )
