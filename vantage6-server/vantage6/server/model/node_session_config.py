from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base


class NodeSessionConfig(Base):
    """
    Table to store node session configuration by key-value pairs.

    This information includes e.g. which databases are available in the session.

    Attributes
    ----------
    node_session_id : int
        ID of the node session that this configuration belongs to
    key : str
        Key of the configuration
    value : str
        Value of the configuration

    Relationships
    -------------
    node_session : :class:`~vantage6.server.model.node_session.NodeSession`
        Node session that this configuration belongs to
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
