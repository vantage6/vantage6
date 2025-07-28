from __future__ import annotations

import bcrypt
from sqlalchemy import Column, ForeignKey, Integer, String, select
from sqlalchemy.orm import relationship, validates

from vantage6.common.globals import AuthStatus

from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.model.base import DatabaseSessionManager


class Node(Authenticatable):
    """
    Table that contains all registered nodes.

    Attributes
    ----------
    id : int
        Primary key
    name : str
        Name of the node
    collaboration_id : int
        ID of the collaboration that the node belongs to
    organization_id : int
        ID of the organization that the node belongs to

    Relationships
    -------------
    collaboration : :class:`~.model.collaboration.Collaboration`
        Collaboration that the node belongs to
    organization : :class:`~.model.organization.Organization`
        Organization that the node belongs to
    config : :class:`~.model.node_config.NodeConfig`
        Configuration of the node
    columns : list[:class:`~.model.column.Column`]
        List of columns that are part of this node. Note that these columns can belong
        to different dataframes.
    """

    id = Column(Integer, ForeignKey("authenticatable.id"), primary_key=True)

    # fields
    name = Column(String, unique=True)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="nodes")
    organization = relationship("Organization", back_populates="nodes")
    config = relationship("NodeConfig", back_populates="node")
    columns = relationship("Column", back_populates="node")

    # the type specification in Authenticatable
    __mapper_args__ = {
        "polymorphic_identity": "node",
    }

    @classmethod
    def get_online_nodes(cls) -> list[Node]:
        """
        Return nodes that currently have status 'online'

        Returns
        -------
        list[Node]
            List of node models that are currently online
        """
        session = DatabaseSessionManager.get_session()

        result = session.scalars(
            select(cls).filter_by(status=AuthStatus.ONLINE.value)
        ).all()
        session.commit()
        return result

    @classmethod
    def get_by_org_and_collab(cls, organization_id: int, collaboration_id: int) -> Node:
        """
        Get a node by organization and collaboration.
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalar(
            select(cls).filter_by(
                organization_id=organization_id, collaboration_id=collaboration_id
            )
        )
        session.commit()
        return result

    @classmethod
    def exists_by_id(cls, organization_id: int, collaboration_id: int) -> bool:
        """
        Check if a node exists for the given organization and collaboration.

        Parameters
        ----------
        organization_id : int
            The id of the organization
        collaboration_id : int
            The id of the collaboration

        Returns
        -------
        bool
            True if a node exists for the given organization and collaboration,
            False otherwise.
        """
        session = DatabaseSessionManager.get_session()
        result = session.scalar(
            select(cls).filter_by(
                organization_id=organization_id, collaboration_id=collaboration_id
            )
        )
        session.commit()
        return result

    def __repr__(self) -> str:
        """
        String representation of the Node model.

        Returns
        -------
        str
            String representation of the Node model
        """
        return (
            "<Node "
            f"{self.id}: '{self.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.collaboration.name}, "
            ">"
        )
