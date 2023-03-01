from __future__ import annotations
from typing import Union
from sqlalchemy import Column, Text, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import Base, DatabaseSessionManager


class Role(Base):
    """Collection of Rules

    Attributes
    ----------
    name : str
        Name of the role
    description : str
        Description of the role
    organization_id : int
        Id of the organization this role belongs to
    rules : List[Rule]
        List of rules that belong to this role
    organization : Organization
        Organization this role belongs to
    users : List[User]
        List of users that belong to this role
    """

    # fields
    name = Column(Text)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    rules = relationship("Rule", back_populates="roles",
                         secondary="role_rule_association")
    organization = relationship("Organization", back_populates="roles")
    users = relationship("User", back_populates="roles",
                         secondary="Permission")

    @classmethod
    def get_by_name(cls, name: str) -> Union[Role, None]:
        """
        Get a role by its name.

        Parameters
        ----------
        name : str
            Name of the role

        Returns
        -------
        Role | None
            Role with the given name or None if no role with the given name
            exists
        """
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
        return (
            f"<Role "
            f"{self.id}: '{self.name}', "
            f"description: {self.description}, "
            f"{len(self.users)} user(s)"
            ">"
        )
