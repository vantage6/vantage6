from __future__ import annotations

from sqlalchemy import Column, String, Integer, ForeignKey, select
from sqlalchemy.orm import relationship

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.algorithm.store.model.rule import Operation, Rule


class User(Base):
    """
    Table to keep track of Users (persons) that can access the system.

    Attributes
    ----------
    username : str
        Username
    email : str
        Email address
    organization_id : int
        Id of the organization to which the user belongs
    v6_server_id : int
        Id of the whitelisted server through which the user is authenticated
    server : :class:`~.model.vantage6_server.Vantage6Server`
        Server through which the user is authenticated
    roles : list[:class:`~.model.role.Role`]
        List of roles that the user has
    algorithms : list[:class:`~.model.algorithm.Algorithm`]
        List of algorithms that the user has developed
    reviews : list[:class:`~.model.review.Review`]
        List of reviews that the user has written
    """

    # fields
    # link with the v6 server. This is a temporary solution
    username = Column(String)
    email = Column(String)
    organization_id = Column(Integer)
    v6_server_id = Column(Integer, ForeignKey("vantage6server.id"))

    # relationships
    server = relationship("Vantage6Server", back_populates="users")
    roles = relationship("Role", back_populates="users", secondary="Permission")
    rules = relationship("Rule", back_populates="users", secondary="UserPermission")

    algorithms = relationship("Algorithm", back_populates="developer")
    reviews = relationship("Review", back_populates="reviewer")

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
            f"id={self.id}, username='{self.username}', roles='{self.roles}', "
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
        return any(rule in role.rules for role in self.roles) or rule in self.rules

    @classmethod
    def get_by_permission(cls, resource: str, operation: Operation) -> list[User]:
        """
        Get all users that have a certain permission

        Parameters
        ----------
        resource: str
            The resource type on which the action is to be performed
        operation: Operation
            The operation a user wants to execute

        Returns
        -------
        list[User]
            List of users that have the requested permission
        """
        return [user for user in cls.get() if user.can(resource, operation)]

    @classmethod
    def get_by_server(cls, username: str, v6_server_id: int) -> User:
        """
        Get a user by their v6 server id

        Parameters
        ----------
        username: str
             username of the user on v6 server
        v6_server_id: int
             id whitelisted v6 server

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
        result = session.scalars(
            select(cls).filter_by(username=username, v6_server_id=v6_server_id)
        ).one_or_none()
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
        result = session.scalars(select(cls).filter_by(username=username)).one()
        session.commit()
        return result

    def is_reviewer(self) -> bool:
        """
        Check if user is allowed to review algorithms

        Returns
        -------
        bool
            Whether or not user is a reviewer
        """
        return self.can("review", Operation.EDIT)
