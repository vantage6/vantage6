from __future__ import annotations
import bcrypt
import datetime as dt

from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, select
from sqlalchemy.orm import relationship, validates

from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.model.rule import Operation, Rule, Scope
from vantage6.server.model.common.utils import validate_password
from vantage6.server.hashedpassword import HashedPassword


class User(Authenticatable):
    """
    Table to keep track of Users (persons) that can access the system.

    Users always belong to an organization and can have certain
    rights within an organization.

    Attributes
    ----------
    username : str
        Username of the user
    password : str
        Password of the user
    firstname : str
        First name of the user
    lastname : str
        Last name of the user
    email : str
        Email address of the user
    organization_id : int
        Foreign key to the organization to which the user belongs
    failed_login_attempts : int
        Number of failed login attempts
    last_login_attempt : datetime.datetime
        Date and time of the last login attempt
    otp_secret : str
        Secret key for one time passwords
    last_email_failed_login_sent : datetime.datetime
        Date and time of the last email sent for failed login
    last_email_recover_password_sent : datetime.datetime
        Date and time of the last email sent for password recovery

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
    password = Column(String)
    firstname = Column(String)
    lastname = Column(String)
    email = Column(String, unique=True)
    organization_id = Column(Integer, ForeignKey("organization.id"))
    failed_login_attempts = Column(Integer, default=0)
    last_login_attempt = Column(DateTime)
    otp_secret = Column(String(32))
    last_email_failed_login_sent = Column(DateTime)
    last_email_recover_password_sent = Column(DateTime)

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

    @validates("password")
    def _validate_password(self, key: str, password: str | HashedPassword) -> str:
        """
        Validate the password of the user by hashing it, as it is also hashed
        in the database. If the password is already hashed (i.e. is an instance
        of HashedPassword), it is returned as is.

        Parameters
        ----------
        key: str
            Name of the attribute (in this case 'password')
        password: str | HashedPassword
            Password of the user

        Returns
        -------
        str
            Hashed password
        """
        if isinstance(password, HashedPassword):
            return password
        else:
            return self.hash(password)

    def set_password(self, pw: str) -> str | None:
        """
        Set the password of the current user.

        Parameters
        ----------
        pw: str
            The new password

        Returns
        -------
        str | None
            If the new password fails to pass the checks, a message is
            returned. Else, none is returned

        Raises
        ------
        ValueError
            If the password is not valid
        """
        try:
            validate_password(pw)
        except ValueError as e:
            return str(e)

        self.password = pw
        self.save()

    def check_password(self, pw: str) -> bool:
        """
        Check if the password is correct

        Parameters
        ----------
        pw: str
            Password to check

        Returns
        -------
        bool
            Whether or not the password is correct
        """
        if self.password is not None:
            expected_hash = self.password.encode("utf8")
            return bcrypt.checkpw(pw.encode("utf8"), expected_hash)
        return False

    def is_blocked(
        self, max_failed_attempts: int, inactivation_in_minutes: int
    ) -> tuple[bool, int | None]:
        """
        Check if user can login or if they are temporarily blocked because they
        entered a wrong password too often

        Parameters
        ----------
        max_failed_attempts: int
            Maximum number of attempts to login before temporary deactivation
        inactivation_in_minutes: int
            How many minutes an account is deactivated

        Returns
        -------
        bool
            Whether or not user is blocked temporarily
        int | None
            How many minutes user is still blocked for
        """
        td_max_blocked = dt.timedelta(minutes=inactivation_in_minutes)
        td_last_login = (
            dt.datetime.now(dt.timezone.utc) - self.last_login_attempt
            if self.last_login_attempt
            else None
        )
        has_max_attempts = (
            self.failed_login_attempts >= max_failed_attempts
            if self.failed_login_attempts
            else False
        )
        if has_max_attempts and td_last_login < td_max_blocked:
            minutes_remaining = (td_max_blocked - td_last_login).seconds // 60 + 1
            return True, minutes_remaining
        else:
            return False, None

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
    def get_by_email(cls, email: str) -> User:
        """
        Get a user by their email

        Parameters
        ----------
        email: str
            Email of the user

        Returns
        -------
        User
            User with the given email

        Raises
        ------
        NoResultFound
            If no user with the given email exists
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalars(select(cls).filter_by(email=email)).one()
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
