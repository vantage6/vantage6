from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.orm import relationship

from vantage6.common.session_status import SessionStatus

from vantage6.server.model.base import Base


class NodeSession(Base):
    """
    Table that tracks the sessions at node level.

    A node session keeps track of which nodes have prepared a session. When a
    session is ready it can be used to execute computation tasks. A single session
    contains multiple nodes, therefore a single session has multiple states. Each node
    session contains also a set of configuration optiosn that are specific to the node
    and session (e.g. which datasets are created within the session).

    Attributes
    ----------
    node : :class:`~vantage6.server.model.node.Node`
        Node that has prepared the session
    session : :class:`~vantage6.server.model.session.Session`
        Session that is prepared by the node
    state : SessionStatus
        State of the session
    last_updated_at : datetime.datetime
        Date and time of the last update of the session state

    Raises
    ------
    IntegrityError
        when the node and session combination already exists
    """

    # fields
    node_id = Column(Integer, ForeignKey("node.id"))
    session_id = Column(Integer, ForeignKey("session.id"))
    state = Column(Enum(SessionStatus), default=SessionStatus.PENDING)
    last_updated_at = Column(DateTime, default=datetime.now(timezone.utc))

    __table_args__ = (UniqueConstraint("node_id", "session_id"), )

    # relationships
    node = relationship("Node", back_populates="sessions")
    session = relationship("Session", back_populates="node_sessions")
    config = relationship("NodeSessionConfig", back_populates="node_session")

    def __repr__(self):
        """
        Returns a string representation of the session state.

        Returns
        -------
        str
            String representation of the session state
        """
        return (
            f"<NodeSession {self.id}, "
            f"node_id={self.node.name}, "
            f"session_id={self.session.label}, "
            f"state={self.state}, "
            ">"
        )
