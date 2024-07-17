from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from vantage6.common.enums import SessionStatus
from vantage6.server.model.rule import Scope
from vantage6.server.model.base import Base

if TYPE_CHECKING:
    from vantage6.server.model.collaboration import Collaboration


class Session(Base):
    """
    Table that describes which sessions are available.

    Sessions allow for users to create a state at the node. This state can be used
    to store data that exchanged between algorithm containers. A session is part of a
    collaboration and owned by a user.

    Attributes
    ----------
    name : str
        Name of the session
    user_id : int
        ID of the user that owns the session
    collaboration_id : int
        ID of the collaboration that this session is part of
    study_id : int
        ID of the study that this session is part of
    created_at : datetime.datetime
        Date and time of the creation of the session
    last_used_at : datetime.datetime
        Date and time of the last usage of the session
    scope : str
        Scope of the session

    Relationships
    -------------
    owner : :class:`~vantage6.server.model.user.User`
        User that owns the session
    collaboration : :class:`~vantage6.server.model.collaboration.Collaboration`
        Collaboration that this session is part of
    study : :class:`~vantage6.server.model.study.Study`
        Study that this session is part of
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are part of this study
    node_sessions : list[:class:`~vantage6.server.model.node_session.NodeSession`]
        List of nodes and their state that are part of this session

    Raises
    ------
    IntegrityError
        If the label already exists within the collaboration
    """

    # fields
    name = Column(String)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"), nullable=False)
    study_id = Column(Integer, ForeignKey("study.id"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_used_at = Column(DateTime, default=datetime.now(timezone.utc))
    scope = Column(String, default=Scope.OWN.value)

    __table_args__ = (UniqueConstraint("name", "collaboration_id"),)

    # relationships
    owner = relationship("User", back_populates="sessions")
    collaboration = relationship("Collaboration", back_populates="sessions")
    study = relationship("Study", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")
    node_sessions = relationship("NodeSession", back_populates="session")
    dataframes = relationship("Dataframe", back_populates="session")

    @property
    def is_ready(self):
        """
        Check if the session is ready to be used.

        Returns
        -------
        bool
            True if the session is ready, False otherwise
        """
        # TODO FM 15-07-2024: we should check all the states of the tasks in the session
        # (not compute) tasks
        return all(
            n_session.state == SessionStatus.READY for n_session in self.node_sessions
        )

    @staticmethod
    def name_exists(name: str, collaboration: "Collaboration"):
        """
        Check if a session with the given name already exists in the collaboration.

        Parameters
        ----------
        name : str
            Name of the session to check

        Returns
        -------
        bool
            True if the session name already exists, False otherwise
        """
        return any(session.name == name for session in collaboration.sessions)

    def organizations(self):
        """
        Returns the organizations that are part of the session. In case a the session
        is scoped to a study, the organizations of the study are returned. Otherwise,
        the organizations of the collaboration are returned.

        Returns
        -------
        list[:class:`~vantage6.server.model.organization.Organization`]
            List of organizations that are part of the session
        """
        if self.study:
            return self.study.organizations
        else:
            return self.collaboration.organizations

    def organization_ids(self):
        """
        Returns the organization IDs that are part of the session. In case a the session
        is scoped to a study, the organization IDs of the study are returned. Otherwise,
        the organization IDs of the collaboration are returned.

        Returns
        -------
        list[int]
            List of organization IDs that are part of the session
        """
        return [org.id for org in self.organizations()]

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
            f"{self.id}: '{self.name}', "
            f"owner_id={self.owner.username}, "
            f"collaboration={self.collaboration.name}, "
            f"{number_of_tasks} task(s)"
            ">"
        )
