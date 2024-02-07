from __future__ import annotations
import bcrypt
import datetime as dt

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship, validates

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.algorithm.store.model.rule import Operation, Rule


class User(Base):
    """
    Table to keep track of Users (persons) that can access the system.

    Users always belong to an organization and can have certain
    rights within an organization.

    Attributes
    ----------
    id_server : int
        User id as saved in the V6 server
    """

    # fields
    # link with the v6 server. This is a temporary solution
    id_server = Column(Integer, unique=True)
    username = Column(String, unique=True)

    # relationships
    roles = relationship("Role", back_populates="users",
                         secondary="Permission")
    # rules = relationship("Rule", back_populates="users",
    #                      secondary="UserPermission")

    algorithms = relationship("Algorithm", back_populates='developer',
                              secondary="developer_algorithm_association")
    reviews = relationship("Review", back_populates="reviewers")

    def __repr__(self) -> str:
        """
        String representation of the user.

        Returns
        -------
        str
            String representation of the user
        """
        return (
            f"<User "
            f"id={self.id}, v6_id='{self.id_server}', roles='{self.roles}', "
            f">"
        )

    def can(self, resource: str, operation: Operation) -> bool:
        """
        Check if user is allowed to execute a certain action

        Parameters
        ---------
        resource: str
            The resource type on which the action is to be performed
        operation: Operation
            The operation a user wants to execute

        Returns
        -------
        bool
            Whether or not user is allowed to execute the requested operation
            on the resource
        """
        rule = Rule.get_by_(resource, operation)
        return any(rule in role.rules for role in self.roles)

    @classmethod
    def get_by_id_server(cls, id_server: int) -> User:
        """
        Get a user by their v6 server id

        Parameters
        ----------
        id_server: int
            v6 server id of the user

        Returns
        -------
        User
            User with the given username

        Raises
        ------
        NoResultFound
            If no user with the given username exists
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(cls).filter_by(id_server=id_server).one()
        session.commit()
        return result

    @classmethod
    def get_by_username(cls, username: str) -> User:
        """
        Get a user by their username

        Parameters
        ----------
        username: str
            Username of the user

        Returns
        -------
        User
            User with the given username

        Raises
        ------
        NoResultFound
            If no user with the given username exists
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(cls).filter_by(username=username).one()
        session.commit()
        return result
