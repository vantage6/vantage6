from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import relationship

from vantage6.hq.model.base import Base, DatabaseSessionManager


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
    uses_hq_keycloak: bool
        Whether the algorithm store authenticates with the same Keycloak as HQ. Only
        then are tokens sent to it.

    Relationships
    -------------
    collaboration: :class:`~vantage6.hq.model.collaboration.Collaboration`
        The collaboration that this algorithm store belongs to or ``None`` if
        it is available for all collaborations.
    tasks: list[:class:`~vantage6.hq.model.task.Task`]
        List of tasks that use this algorithm store
    """

    # fields
    name = Column(String)
    url = Column(String)
    api_path = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    uses_hq_keycloak = Column(Boolean, default=False)

    # relationships
    collaboration = relationship("Collaboration", back_populates="algorithm_stores")
    tasks = relationship("Task", back_populates="algorithm_store")

    @classmethod
    def get_by_url(cls, url: str, api_path: str) -> list[AlgorithmStore]:
        """
        Get all algorithm store records with a certain url

        Parameters
        ----------
        url : str
            The url of the algorithm store
        api_path : str
            The api path of the algorithm store

        Returns
        -------
        list[AlgorithmStore]
            List of algorithm store records with that URL
        """
        session = DatabaseSessionManager.get_session()
        results = session.scalars(
            select(AlgorithmStore).filter_by(url=url, api_path=api_path)
        ).all()
        session.commit()
        return results

    @classmethod
    def set_uses_hq_keycloak(cls, url: str, api_path: str, value: bool) -> None:
        """
        Set whether an algorithm store uses the same Keycloak as HQ, on all records of
        that store.

        Parameters
        ----------
        url : str
            The url of the algorithm store
        api_path : str
            The api path of the algorithm store
        value : bool
            Whether the algorithm store uses the same Keycloak as HQ
        """
        for store in cls.get_by_url(url, api_path):
            store.uses_hq_keycloak = value
            store.save()

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
