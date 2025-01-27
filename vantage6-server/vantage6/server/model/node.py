from __future__ import annotations
import bcrypt

from sqlalchemy.orm import relationship, validates
from sqlalchemy import Column, Integer, String, ForeignKey, select

from vantage6.common.globals import AuthStatus
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.authenticatable import Authenticatable


class Node(Authenticatable):
    """
    Table that contains all registered nodes.

    Attributes
    ----------
    id : int
        Primary key
    name : str
        Name of the node
    api_key : str
        API key of the node
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

    _hidden_attributes = ["api_key"]

    id = Column(Integer, ForeignKey("authenticatable.id"), primary_key=True)

    # fields
    name = Column(String, unique=True)
    api_key = Column(String)
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

    @validates("api_key")
    def _validate_api_key(self, key: str, api_key: str) -> str:
        """
        Hashes the api_key before storing it in the database.

        Parameters
        ----------
        key : str
            The name of the attribute that is being validated
        api_key : str
            The value of the attribute that is being validated

        Returns
        -------
        str
            The hashed api_key
        """
        return self.hash(api_key)

    def check_key(self, key: str) -> bool:
        """
        Checks if the provided key matches the stored key.

        Parameters
        ----------
        key : str
            The key to check

        Returns
        -------
        bool
            True if the provided key matches the stored key, False otherwise
        """
        if self.api_key is not None:
            expected_hash = self.api_key.encode("utf8")
            return bcrypt.checkpw(key.encode("utf8"), expected_hash)
        return False

    @classmethod
    def get_by_api_key(cls, api_key: str) -> Node | None:
        """
        Returns Node based on the provided API key.

        Parameters
        ----------
        api_key : str
            The API key of the node to search for

        Returns
        -------
        Node | None
            Returns the node if a node is associated with api_key, None if no
            node is associated with api_key.
        """
        session = DatabaseSessionManager.get_session()

        nodes = session.scalars(select(cls)).all()
        session.commit()
        for node in nodes:
            is_correct_key = node.check_key(api_key)
            if is_correct_key:
                return node
        # no node found with matching API key
        return None

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
            f"api_key: {self.api_key} "
            ">"
        )
