from sqlalchemy import Column, String

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager
from vantage6.common.enum import StorePolicies


class Policy(Base):
    """
    Table that describes the policies of this algorithm store.

    Attributes
    ----------
    key: str
        Key of the setting
    value: str
        Value of the setting
    """

    key = Column(String)
    value = Column(String)

    @classmethod
    def get_servers_allowed_to_be_whitelisted(cls) -> list[str]:
        """
        Get the servers that are allowed to be whitelisted.

        Returns
        -------
        list[str]
            List of servers that are allowed to be whitelisted
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(cls).filter_by(key=StorePolicies.ALLOWED_SERVERS).all()
        session.commit()
        return [r.value for r in result]

    @classmethod
    def is_localhost_allowed_to_be_whitelisted(cls) -> bool:
        """
        Check if localhost is allowed to be whitelisted.

        Returns
        -------
        bool
            True if localhost is allowed to be whitelisted, False otherwise
        """
        session = DatabaseSessionManager.get_session()
        result = (
            session.query(cls)
            .filter_by(key=StorePolicies.ALLOW_LOCALHOST)
            .one_or_none()
        )
        session.commit()
        if result is None:
            return False
        return result.value == "True" or result.value == "1"

    @classmethod
    def get_servers_with_edit_permission(cls) -> list[str]:
        """
        Get the servers that have edit permission.

        Returns
        -------
        list[str]
            List of servers that have edit permission
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(cls).filter_by(key=StorePolicies.ALLOWED_SERVERS).all()
        session.commit()
        return [r.value for r in result]
