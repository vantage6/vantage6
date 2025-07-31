from typing import Self

import bcrypt
from sqlalchemy import Column, DateTime, String, select

from vantage6.server.model.base import Base, DatabaseSessionManager


class Authenticatable(Base):
    """
    Parent table of database entities that can authenticate.

    Entities that can authenticate are nodes and users. Containers
    can also authenticate but these are authenticated indirectly
    through the nodes.
    """

    # fields
    type = Column(String(50))
    __mapper_args__ = {
        "polymorphic_identity": "authenticatable",
        "polymorphic_on": type,
    }
    keycloak_id = Column(String)
    last_seen = Column(DateTime)
    status = Column(String)
    keycloak_client_id = Column(String, nullable=True)

    @staticmethod
    def hash(secret: str) -> str:
        """
        Hash a secret using bcrypt.

        Parameters
        ----------
        secret : str
            Secret to be hashed

        Returns
        -------
        str
            Hashed secret
        """
        return bcrypt.hashpw(secret.encode("utf8"), bcrypt.gensalt()).decode("utf8")

    @staticmethod
    def get_by_keycloak_id(keycloak_id: str) -> Self:
        """
        Get an authenticatable entity by its keycloak ID.

        Parameters
        ----------
        keycloak_id : str
            The keycloak ID of the authenticatable entity

        Returns
        -------
        Authenticatable
            The authenticatable entity
        """
        session = DatabaseSessionManager.get_session()
        return session.scalars(
            select(Authenticatable).filter(Authenticatable.keycloak_id == keycloak_id)
        ).one_or_none()
