from __future__ import annotations

from sqlalchemy import Column, String, Integer, select
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
    organization_id : int
        Id of the organization to which the user belongs
    keycloak_id : str
        Id of the keycloak user
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
    organization_id = Column(Integer)
    keycloak_id = Column(String)

    # relationships
    roles = relationship("Role", back_populates="users", secondary="Permission")
    rules = relationship("Rule", back_populates="users", secondary="UserPermission")

    algorithms = relationship("Algorithm", back_populates="developer")
    reviews = relationship(
        "Review", foreign_keys="Review.reviewer_id", back_populates="reviewer"
    )
    requested_reviews = relationship(
        "Review", foreign_keys="Review.requested_by_id", back_populates="requested_by"
    )

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
    def get_by_keycloak_id(cls, keycloak_id: str) -> User | None:
        """
        Get a user by their keycloak id

        Parameters
        ----------
        keycloak_id: str
            The keycloak id of the user

        Returns
        -------
        User | None
            The user with the given keycloak id, or None if the user does not exist
        """
        session = DatabaseSessionManager.get_session()
        return session.scalars(
            select(cls).filter_by(keycloak_id=keycloak_id)
        ).one_or_none()

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
    def get_by_username(cls, username: str) -> User | None:
        """
        Get a user by their username

        Parameters
        ----------
        username: str
            Username of the user

        Returns
        -------
        User | None
            User with the given username, or None if the user does not exist

        Raises
        ------
        NoResultFound
            If no user with the given username exists
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls).filter_by(username=username)).one_or_none()
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
