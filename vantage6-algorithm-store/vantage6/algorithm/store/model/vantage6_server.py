from __future__ import annotations
from sqlalchemy import Column, String

from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager


class Vantage6Server(Base):
    """
    Table that describes which vantage6 central servers this algorithm store is
    linked to. It essentially serves as a whitelist of servers that are allowed
    to use this algorithm store.

    Attributes
    ----------
    url : str
        URL of the vantage6 server
    """

    # fields
    url = Column(String)

    @classmethod
    def get_by_url(cls, url: str) -> Vantage6Server | None:
        """
        Get all algorithm store records with a certain url

        Parameters
        ----------
        url : str
            The url of the algorithm store

        Returns
        -------
        Vanatge6Server | None
            Vanatge6Server object if found, None otherwise
        """
        session = DatabaseSessionManager.get_session()
        return session.query(Vantage6Server).filter_by(url=url).first()
