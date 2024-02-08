from __future__ import annotations
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, DatabaseSessionManager


class AlgorithmStore(Base):
    """
    Table that describes which algorithm stores are available for which
    collaborations.

    Attributes
    ----------
    name: str
        The name of the algorithm store
    url: str
        The url of the algorithm store
    collaboration_id: int
        The id of the
        :class:`~vantage6.server.model.collaboration.Collaboration` that this
        algorithm store belongs to. If it is ``None``, then it is available for
        all collaborations.
    """

    # fields
    name = Column(String)
    url = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))

    collaboration = relationship("Collaboration", back_populates="algorithm_stores")

    @classmethod
    def get_by_url(cls, url: str) -> list[AlgorithmStore]:
        """
        Get all algorithm store records with a certain url

        Parameters
        ----------
        url : str
            The url of the algorithm store

        Returns
        -------
        list[AlgorithmStore]
            List of algorithm store records with that URL
        """
        session = DatabaseSessionManager.get_session()
        return session.query(AlgorithmStore).filter_by(url=url).all()
