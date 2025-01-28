from __future__ import annotations
from sqlalchemy import Column, String, Boolean, select
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from vantage6.server.model.base import Base, DatabaseSessionManager
from vantage6.server.model.node import Node
from vantage6.server.model.organization import Organization


class Collaboration(Base):
    """
    Table that describes which collaborations are available.

    Collaborations are combinations of one or more organizations
    that do studies together. Each
    :class:`~vantage6.server.model.organization.Organization` has a
    :class:`~vantage6.server.model.node.Node` for
    each collaboration that it is part of. Within a collaboration multiple
    :class:`~vantage6.server.model.task.Task` can be executed.

    Attributes
    ----------
    name : str
        Name of the collaboration
    encrypted : bool
        Whether the collaboration is encrypted or not
    session_restrict_to_same_image : bool
        when set to True, enforces that all functions calls in a single session must
        originate from the same image

    Relationships
    -------------
    organizations :
            list[:class:`~vantage6.server.model.organization.Organization`]
        List of organizations that are part of this collaboration
    nodes : list[:class:`~vantage6.server.model.node.Node`]
        List of nodes that are part of this collaboration
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are part of this collaboration
    studies : list[:class:`~vantage6.server.model.study.Study`]
        List of studies that are part of this collaboration
    sessions : list[:class:`~vantage6.server.model.session.Session`]
        List of sessions that are part of this collaboration
    algorithm_stores : list[:class:`~vantage6.server.model.algorithm_store.AlgorithmStore`]
        List of algorithm stores that are part of this collaboration

    """

    # fields
    name = Column(String, unique=True)
    encrypted = Column(Boolean, default=1)
    session_restrict_to_same_image = Column(Boolean, default=0)

    # relationships
    organizations = relationship(
        "Organization", secondary="Member", back_populates="collaborations"
    )
    nodes = relationship("Node", back_populates="collaboration")
    tasks = relationship("Task", back_populates="collaboration")
    studies = relationship("Study", back_populates="collaboration")
    sessions = relationship("Session", back_populates="collaboration")
    algorithm_stores = relationship("AlgorithmStore", back_populates="collaboration")

    def get_organization_ids(self) -> list[int]:
        """
        Returns a list of organization ids that are part of this collaboration.

        Returns
        -------
        list[int]
            List of organization ids
        """
        return [organization.id for organization in self.organizations]

    def get_task_ids(self) -> list[int]:
        """
        Returns a list of task ids that are part of this collaboration.

        Returns
        -------
        list[int]
            List of task ids
        """
        return [task.id for task in self.tasks]

    def get_nodes_from_organizations(self, ids: list[int]) -> list[Node]:
        """
        Returns a subset of nodes that are part of the given organizations.

        Parameters
        ----------
        ids : list[int]
            List of organization ids

        Returns
        -------
        list[:class:`~vantage6.server.model.node.Node`]
            List of nodes that are part of the given organizations
        """
        return [n for n in self.nodes if n.organization.id in ids]

    def get_node_from_organization(self, organization: Organization) -> Node | None:
        """
        Returns the node that is part of the given
        :class:`~vantage6.server.model.organization.Organization`.

        Parameters
        ----------
        organization: :class:`~vantage6.server.model.organization.Organization`
            Organization to get node from

        Returns
        -------
        :class:`~vantage6.server.model.node.Node` | None
            Node for the given organization for this collaboration, or None if
            there is no node for the given organization.
        """
        for node in self.nodes:
            if node.organization.id == organization.id:
                return node
        return None

    @classmethod
    def find_by_name(cls, name: str) -> Collaboration | None:
        """
        Find :class:`.Collaboration` by its name.

        Parameters
        ----------
        name: str
            Name of the collaboration

        Returns
        -------
        Collaboration | None
            Collaboration with the given name, or None if no collaboration
            with the given name exists.
        """
        session = DatabaseSessionManager.get_session()
        try:
            result = session.scalars(select(cls).filter_by(name=name)).first()
            session.commit()
            return result
        except NoResultFound:
            return None

    def __repr__(self) -> str:
        """
        Returns a string representation of the collaboration.

        Returns
        -------
        str
            String representation of the collaboration
        """
        number_of_organizations = len(self.organizations)
        number_of_tasks = len(self.tasks)
        return (
            "<Collaboration "
            f"{self.id}: '{self.name}', "
            f"{number_of_organizations} organization(s), "
            f"{number_of_tasks} task(s)"
            ">"
        )
