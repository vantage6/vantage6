from sqlalchemy import Column, ForeignKey, Text, Integer
from sqlalchemy.orm import relationship

from .base import Base
from .task import Task
from .organization import Organization


class TaskAssignment(Base):
    """Assigns Task to a Organization.
    
    A organization is assigned a Task and it encrypted input for a specific 
    organization. It is not possible for anyone else but the receiving organization
    to read the input values.
    """
    __tablename__ = "task_assignment"

    # fields
    input = Column(Text)
    task_id = Column(Integer, ForeignKey("task.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))

    # relationships
    task = relationship("Task", back_populates="task_assignment")
    organization = relationship("Organization", 
        back_populates="task_assignment")
    result = relationship("Result", back_populates="task_assignment")

    def __repr__(self):
        return f"<task:{self.task.name}, organization:{self.organization.name}>"
