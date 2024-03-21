from __future__ import annotations

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    Enum,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from vantage6.common.session_status import SessionStatus
from vantage6.server.model.rule import Scope
from vantage6.server.model.base import Base


class Session(Base):
    """
    Table that describes which sessions are available.

    Sessions allow for users to create a state at the node. This state can be used
    to store data that exchanged between algorithm containers. A session is part of a
    collaboration and owned by a user.

    Attributes
    ----------
    label : str
        Label of the session
    owner : :class:`~vantage6.server.model.user.User`
        User that owns the session
    collaboration : :class:`~vantage6.server.model.collaboration.Collaboration`
        Collaboration that this session is part of
    created_at : datetime.datetime
        Date and time of the creation of the session
    last_used_at : datetime.datetime
        Date and time of the last usage of the session
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are part of this study
    node_sessions : list[:class:`~vantage6.server.model.node_session.NodeSession`]
        List of nodes and their state that are part of this session
    scope : Scope
        Scope of the session

    Raises
    ------
    IntegrityError
        If the label already exists within the collaboration
    """

    # fields
    label = Column(String)
    user_id = Column(Integer, ForeignKey("user.id"))
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_used_at = Column(DateTime, default=datetime.now(timezone.utc))
    scope = Column(Enum(Scope), default=Scope.OWN)

    __table_args__ = (UniqueConstraint("label", "collaboration_id"),)

    # relationships
    owner = relationship("User", back_populates="sessions")
    collaboration = relationship("Collaboration", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")
    node_sessions = relationship("NodeSession", back_populates="session")

    @property
    def is_ready(self):
        """
        Check if the session is ready to be used.

        Returns
        -------
        bool
            True if the session is ready, False otherwise
        """
        return all(
            n_session.state == SessionStatus.READY for n_session in self.node_sessions
        )

    def __repr__(self):
        """
        Returns a string representation of the session.

        Returns
        -------
        str
            String representation of the session
        """
        number_of_tasks = len(self.tasks)
        return (
            "<Session "
            f"{self.id}: '{self.label}', "
            f"owner_id={self.owner.username}, "
            f"collaboration={self.collaboration.name}, "
            f"{number_of_tasks} task(s)"
            ">"
        )
