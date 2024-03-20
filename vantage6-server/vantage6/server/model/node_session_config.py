from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import Base


class NodeSessionConfig(Base):
    """
    Table to store node configuration by key-value pairs.

    This information includes e.g. which algorithms are allowed on a certain
    node. The information is stored in the database while the node is
    connected.
    """

    # fields
    node_session_id = Column(Integer, ForeignKey("nodesession.id"))
    key = Column(String)
    value = Column(String)

    # relationships
    node_session = relationship("NodeSession", back_populates="config")

    def __repr__(self):
        """
        Returns a string representation of the node session configuration.

        Returns
        -------
        str
            String representation of the node session configuration
        """
        return (
            f"<NodeSessionConfig {self.id}, "
            f"node_session_id={self.node_session_id}, "
            f"key={self.key}, "
            f"value={self.value}>"
        )
