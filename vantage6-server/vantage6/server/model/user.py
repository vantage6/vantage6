from __future__ import annotations

from sqlalchemy import Column, String, Integer, ForeignKey, select, Boolean
from sqlalchemy.orm import relationship

from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.model.rule import Operation, Rule, Scope


class User(Authenticatable):
    """
    Table to keep track of Users (persons) that can access the system.

    Users always belong to an organization and can have certain
    rights within an organization.

    Attributes
    ----------
    username : str
        Username of the user
    organization_id : int
        Foreign key to the organization to which the user belongs
    is_service_account : bool
        Whether the user is a service account. Default is False.

    Relationships
    -------------
    organization : :class:`~.model.organization.Organization`
        Organization to which the user belongs
    roles : list[:class:`~.model.role.Role`]
        Roles that the user has
    rules : list[:class:`~.model.rule.Rule`]
        Rules that the user has
    created_tasks : list[:class:`~.model.task.Task`]
        Tasks that the user has created
    sessions : list[:class:`~.model.session.Session`]
        Sessions that the user has created
    """

    _hidden_attributes = ["password"]

    # overwrite id with linked id to the authenticatable
    id = Column(Integer, ForeignKey("authenticatable.id"), primary_key=True)
    __mapper_args__ = {
        "polymorphic_identity": "user",
    }

    # fields
    username = Column(String, unique=True)
    organization_id = Column(Integer, ForeignKey("organization.id"))
    is_service_account = Column(Boolean, default=False)

    # relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", back_populates="users", secondary="Permission")
    rules = relationship("Rule", back_populates="users", secondary="UserPermission")
    created_tasks = relationship("Task", back_populates="init_user")
    sessions = relationship("Session", back_populates="owner")

    def __repr__(self) -> str:
        """
        String representation of the user.

        Returns
        -------
        str
            String representation of the user
        """
        organization = self.organization.name if self.organization else "None"
        return (
            f"<User "
            f"id={self.id}, username='{self.username}', roles='{self.roles}', "
            f"organization='{organization}'"
            f">"
        )

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

    @classmethod
    def get_first_user(cls) -> User:
        """
        Get a random user by their username.

        This function is used to prevent an attacker from finding out which
        usernames exist.

        Returns
        -------
        User
            A random user that is in the database
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls).order_by(cls.id)).first()
        session.commit()
        return result

    @classmethod
    def username_exists(cls, username) -> bool:
        """
        Check if a user with the given username exists

        Parameters
        ----------
        username: str
            Username to check

        Returns
        -------
        bool
            Whether or not a user with the given username exists
        """
        return cls.exists(field="username", value=username)

    def can(self, resource: str, scope: Scope, operation: Operation) -> bool:
        """
        Check if user is allowed to execute a certain action

        Parameters
        ---------
        resource: str
            The resource type on which the action is to be performed
        scope: Scope
            The scope within which the user wants to perform an action
        operation: Operation
            The operation a user wants to execute

        Returns
        -------
        bool
            Whether or not user is allowed to execute the requested operation
            on the resource
        """
        rule = Rule.get_by_(resource, scope, operation)
        return rule in self.rules or any(rule in role.rules for role in self.roles)
