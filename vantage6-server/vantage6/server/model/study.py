from __future__ import annotations
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base


class Study(Base):
    """
    Table that describes which studies are available.

    Studies are subsets of one or more organizations within a collaboration that
    collaborate on a particular research question. Studies use the same nodes and data
    as the collaboration they are part of, and also inherit their collaboration's
    settings.

    Attributes
    ----------
    name : str
        Name of the study
    collaboration_id : int
        ID of the collaboration that this study is part of

    Relationships
    -------------
    collaboration : :class:`~vantage6.server.model.collaboration.Collaboration`
        Collaboration that this study is part of
    organizations :
            list[:class:`~vantage6.server.model.organization.Organization`]
        List of organizations that are part of this study
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are part of this study
    sessions : list[:class:`~vantage6.server.model.session.Session`]
        List of sessions that are part of this study
    """

    # fields
    name = Column(String, unique=True)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="studies")
    organizations = relationship(
        "Organization", secondary="StudyMember", back_populates="studies"
    )
    tasks = relationship("Task", back_populates="study")
    sessions = relationship("Session", back_populates="study")

    def __repr__(self):
        """
        Returns a string representation of the study.

        Returns
        -------
        str
            String representation of the study
        """
        number_of_organizations = len(self.organizations)
        number_of_tasks = len(self.tasks)
        return (
            "<Study "
            f"{self.id}: '{self.name}', "
            f"collaboration_id={self.collaboration_id}, "
            f"{number_of_organizations} organization(s), "
            f"{number_of_tasks} task(s)"
            ">"
        )
