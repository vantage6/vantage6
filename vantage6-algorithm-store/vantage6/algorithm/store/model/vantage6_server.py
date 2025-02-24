from __future__ import annotations
from sqlalchemy import Column, String, or_, select
from sqlalchemy.orm import relationship

from vantage6.common.globals import Ports
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
    users : list[:class:`~.model.user.User`]
        List of known vantage6 users from that server
    """

    # fields
    url = Column(String, unique=True)

    # relationships
    users = relationship("User", back_populates="server")

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

        def _get_by_url(url):
            return session.scalars(select(Vantage6Server).filter_by(url=url)).first()

        session = DatabaseSessionManager.get_session()
        server = _get_by_url(url)
        if not server:
            if url.startswith("https") and url.endswith(str(Ports.HTTPS.value)):
                url = url[:-4]
                server = _get_by_url(url)
            elif url.startswith("http") and url.endswith(str(Ports.HTTP.value)):
                url = url[:-3]
                server = _get_by_url(url)
        return server

    @classmethod
    def get_localhost_servers(cls) -> list[Vantage6Server]:
        """
        Get all algorithm store records with a localhost url

        Returns
        -------
        list[Vantage6Server]
            List of Vantage6Server objects
        """
        session = DatabaseSessionManager.get_session()
        servers = session.scalars(
            select(Vantage6Server).filter(
                or_(
                    Vantage6Server.url.like("http://localhost%"),
                    Vantage6Server.url.like("http://127.0.0.1%"),
                )
            )
        ).all()
        return servers
