from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from .base import Base


class TaskDatabase(Base):
    """
    Table to store which databases are used by which tasks.

    Each line contains a database label of a database that will be used for a
    task with a certain ``task_id``. Each task will usually have zero, one or
    multiple databases assigned to it.
    """

    # fields
    task_id = Column("task_id", Integer, ForeignKey("task.id"))
    database = Column(String)
    parameters = Column(String)

    # relationships
    task = relationship("Task", back_populates="databases")
