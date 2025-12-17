from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base
from vantage6.server.model.collaboration import Collaboration
from vantage6.server.model.rule import Scope


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
    image : str
        Image that is used in the session. This field is only used if the collaboration
        is set to restrict the image to be the same for all tasks in the session.

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
    dataframes : list[:class:`~vantage6.server.model.dataframe.Dataframe`]
        List of dataframes that are part of this session

    Raises
    ------
    IntegrityError
        If the name already exists within the collaboration
    """

    # fields
    name = Column(String)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"), nullable=False)
    study_id = Column(Integer, ForeignKey("study.id"))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    last_used_at = Column(DateTime, default=datetime.now(timezone.utc))
    scope = Column(String, default=Scope.OWN.value)
    image = Column(String)

    __table_args__ = (UniqueConstraint("name", "collaboration_id"),)

    # relationships
    owner = relationship("User", back_populates="sessions")
    collaboration = relationship("Collaboration", back_populates="sessions")
    study = relationship("Study", back_populates="sessions")
    tasks = relationship("Task", back_populates="session")
    dataframes = relationship("Dataframe", back_populates="session")

    def is_ready(self) -> bool:
        """
        Does the session contain at least one dataframe ready to be used by compute
        tasks?

        Returns
        -------
        bool
            True if the session is ready, False otherwise
        """
        for dataframe in self.dataframes:
            if dataframe.ready():
                return True

        return False

    @staticmethod
    def name_exists(name: str, collaboration: Collaboration) -> bool:
        """
        Check if a session with the given name already exists in the collaboration.

        Parameters
        ----------
        name : str
            Name of the session to check
        collaboration : :class:`~vantage6.server.model.collaboration.Collaboration`
            Collaboration to check the session name in

        Returns
        -------
        bool
            True if the session name already exists, False otherwise
        """
        return any(session.name == name for session in collaboration.sessions)

    def organizations(self) -> list:
        """
        Returns the organizations that are part of the session. In case the session
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

    def organization_ids(self) -> list[int]:
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

    def delete(self) -> None:
        """
        Deletes the current session along with its associated dataframes, tasks, and
        results.
        """

        for dataframe in self.dataframes:
            dataframe.delete()

        for task in self.tasks:
            for result in task.results:
                result.delete()
            task.delete()

        super().delete()

    def __repr__(self) -> str:
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
            f"owner_id={self.owner.username if self.owner else None}, "
            f"collaboration={self.collaboration.name if self.collaboration else None}, "
            f"{number_of_tasks} task(s)"
            ">"
        )
