import datetime

from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.server.model.base import Base


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

    # relationships
    task = relationship("Task", back_populates="results")
    organization = relationship("Organization", back_populates="results")

    @hybrid_property
    def complete(self):
        return self.finished_at is not None

    def __repr__(self):
        return (
            "<Result "
            f"{self.id}: '{self.task.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.task.collaboration.name}, "
            f"completed: {self.complete}"
            ">"
        )
