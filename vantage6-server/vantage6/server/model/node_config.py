from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import Base


class NodeConfig(Base):
    """
    Table to store node configuration by key-value pairs.

    This information includes e.g. which algorithms are allowed on a certain
    node. The information is stored in the database while the node is
    connected.
    """

    # fields
    node_id = Column("node_id", Integer, ForeignKey("node.id"))
    key = Column(String)
    value = Column(String)

    # relationships
    node = relationship("Node", back_populates="config")
