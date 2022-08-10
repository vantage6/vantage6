import bcrypt
import re
import datetime as dt

from typing import Union
from sqlalchemy import Column, String, Integer, ForeignKey, exists, DateTime
from sqlalchemy.orm import relationship, validates

from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.authenticable import Authenticatable


class User(Authenticatable):
    """User (person) that can access the system.

    Users always belong to an organization and can have certain
    rights within an organization.
    """
    _hidden_attributes = ['password']

    # overwrite id with linked id to the authenticatable
    id = Column(Integer, ForeignKey('authenticatable.id'), primary_key=True)
    __mapper_args__ = {
        'polymorphic_identity': 'user',
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

    # relationships
    organization = relationship("Organization", back_populates="users")
    roles = relationship("Role", back_populates="users",
                         secondary="Permission")
    rules = relationship("Rule", back_populates="users",
                         secondary="UserPermission")

    def __repr__(self):
        organization = self.organization.name if self.organization else "None"
        return (
            f"<User "
            f"id={self.id}, username='{self.username}', roles='{self.roles}', "
            f"organization='{organization}'"
            f">"
        )

    @validates("password")
    def _validate_password(self, key, password):
        return self.hash(password)

    def set_password(self, pw) -> Union[str, None]:
        """
        Set the password of the current user. This function doesn't save the
        new password to the database

        Parameters
        ----------
        pw: str
            The new password

        Returns
        -------
        str | None
            If the new password fails to pass the checks, a message is
            returned. Else, none is returned
        """
        if len(pw) < 8:
            return (
                "Password too short: use at least 8 characters with mixed "
                "lowercase, uppercase, numbers and special characters"
            )
        elif len(pw) > 128:
            # because long passwords can be used for DoS attacks (long pw
            # hashing consumes a lot of resources)
            return "Password too long: use at most 128 characters"
        elif re.search('[0-9]', pw) is None:
            return "Password should contain at least one number"
        elif re.search('[A-Z]', pw) is None:
            return "Password should contain at least one uppercase letter"
        elif re.search('[a-z]', pw) is None:
            return "Password should contain at least one lowercase letter"
        elif pw.isalnum():
            return "Password should contain at least one special character"

        self.password = pw
        self.save()

    def check_password(self, pw):
        if self.password is not None:
            expected_hash = self.password.encode('utf8')
            return bcrypt.checkpw(pw.encode('utf8'), expected_hash)
        return False

    def is_blocked(self, max_failed_attempts: int,
                   inactivation_in_minutes: int):
        """
        Check if user can login or if they are temporarily blocked because they
        entered a wrong password too often

        Parameters
        ----------
        max_failed_attempts: int
            Maximum number of attempts to login before temporary deactivation
        inactivation_minutes: int
            How many minutes an account is deactivated

        Returns
        -------
        bool
            Whether or not user is blocked temporarily
        str | None
            Message if user is blocked, else None
        """
        td_max_blocked = dt.timedelta(minutes=inactivation_in_minutes)
        td_last_login = dt.datetime.now() - self.last_login_attempt \
            if self.last_login_attempt else None
        has_max_attempts = (
            self.failed_login_attempts >= max_failed_attempts
            if self.failed_login_attempts else False
        )
        if has_max_attempts and td_last_login < td_max_blocked:
            minutes_remaining = \
                (td_max_blocked - td_last_login).seconds // 60 + 1
            return True, (
                f"Your account is blocked for the next {minutes_remaining} "
                "minutes due to failed login attempts. Please wait or "
                "reactivate your account via email."
            )
        else:
            return False, None

    @classmethod
    def get_by_username(cls, username):
        session = DatabaseSessionManager.get_session()
        return session.query(cls).filter_by(username=username).one()

    @classmethod
    def get_by_email(cls, email):
        session = DatabaseSessionManager.get_session()
        return session.query(cls).filter_by(email=email).one()

    @classmethod
    def get_user_list(cls, filters=None):
        session = DatabaseSessionManager.get_session()
        return session.query(cls).all()

    @classmethod
    def username_exists(cls, username):
        session = DatabaseSessionManager.get_session()
        return session.query(exists().where(cls.username == username))\
            .scalar()

    @classmethod
    def exists(cls, field, value):
        session = DatabaseSessionManager.get_session()
        return session.query(exists().where(getattr(cls, field) == value))\
            .scalar()
