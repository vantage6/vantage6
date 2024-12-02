from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base


class NodeConfig(Base):
    """
    Table to store node configuration by key-value pairs.

    This information includes e.g. which algorithms are allowed on a certain
    node. The information is stored in the database while the node is
    connected.

    Attributes
    ----------
    node_id : int
        ID of the node that this configuration belongs to
    key : str
        Key of the configuration
    value : str
        Value of the configuration

    Relationships
    -------------
    node : :class:`~.model.node.Node`
        Node that this configuration belongs to
    """

    # fields
    node_id = Column("node_id", Integer, ForeignKey("node.id"))
    key = Column(String)
    value = Column(String)

    # relationships
    node = relationship("Node", back_populates="config")
