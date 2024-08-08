import bcrypt

from sqlalchemy import Column, String, DateTime

from vantage6.server.model.base import Base


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
    ip = Column(String)
    last_seen = Column(DateTime)
    status = Column(String)

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
