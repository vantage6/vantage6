
from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.server.model import Base, Database


class Role(Base):
    """Rules to determine permissions in an API endpoint.
    """

    # fields
    name = Column(Text)
    description = Column(Text)
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    organization = relationship("Organization", back_populates="Roles")
    users = relationship("User", back_populates="roles", secondary="Permission")

    # fields
    # input = Column(Text)
    # task_id = Column(Integer, ForeignKey("task.id"))
    # organization_id = Column(Integer, ForeignKey("organization.id"))
    # result = Column(Text)
    # assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    # started_at = Column(DateTime)
    # finished_at = Column(DateTime)
    # log = Column(Text)

    # # relationships
    # task = relationship("Task", back_populates="results")
    # organization = relationship("Organization", back_populates="results")

    # @hybrid_property
    # def complete(self):
    #     return self.finished_at is not None

    def __repr__(self):
        return (
            "<Role {self.id} "
            f"name:, {self}"
            ">"
        )
