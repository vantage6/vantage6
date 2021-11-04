import datetime
from flask.globals import session

from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.server.model.base import Base


from vantage6.server.model import (
    Node,
    Collaboration,
    Task,
    Organization
)
from vantage6.server.model.base import DatabaseSessionManager

class Result(Base):
    """Result of a Task as executed by a Node.

    The result (and the input) is encrypted and can be only read by the
    intended receiver of the message.
    """

    # fields
    input = Column(Text)
    task_id = Column(Integer, ForeignKey("task.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))
    result = Column(Text)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log = Column(Text)
    port = Column(Integer)

    # relationships
    task = relationship("Task", back_populates="results")
    organization = relationship("Organization", back_populates="results")

    @property
    def node(self):
        session = DatabaseSessionManager.get_session()
        node = session.query(Node)\
            .join(Collaboration)\
            .join(Organization)\
            .join(Result)\
            .join(Task)\
            .filter(Result.id == self.id)\
            .filter(self.organization_id == Node.organization_id)\
            .filter(Task.collaboration_id == Node.collaboration_id)\
            .one()
        return node

    @hybrid_property
    def complete(self):
        return self.finished_at is not None

    def __repr__(self):
        return (
            "<Result "
            f"{self.id}: '{self.task.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.task.collaboration.name}, "
            f"is_complete: {self.complete}"
            ">"
        )
