from __future__ import annotations
from sqlalchemy import Column, String, Integer, ForeignKey, select
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base, DatabaseSessionManager


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
        The collaboration ID of the collaboration that this algorithm store belongs to.
        If it is ``None``, then it is available for all collaborations.

    Relationships
    -------------
    collaboration: :class:`~vantage6.server.model.collaboration.Collaboration`
        The collaboration that this algorithm store belongs to or ``None`` if
        it is available for all collaborations.
    tasks: list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that use this algorithm store
    """

    # fields
    name = Column(String)
    url = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="algorithm_stores")
    tasks = relationship("Task", back_populates="algorithm_store")

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
        results = session.scalars(select(AlgorithmStore).filter_by(url=url)).all()
        session.commit()
        return results

    def is_for_all_collaborations(self) -> bool:
        """
        Check if the algorithm store is available for all collaborations

        Returns
        -------
        bool
            True if the algorithm store is available for all collaborations,
            False otherwise
        """
        return self.collaboration_id is None
