from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base


class TaskDatabase(Base):
    """
    Table to store which databases are used by which tasks.

    Each record contains a database label or handle to refer to a database that will be
    used for a task with ID ``task_id``. Each task will usually have zero, one or
    multiple databases assigned to it.

    The difference between a source and a handle is that a source is a database that
    contains the data that has been made available to a node. A handle is a database
    that is used to identify a dataframe within a session.

    Typically *data extraction* tasks will have a source database, while
    *pre-processing* and *compute* tasks will have a handle database.

    Attributes
    ----------
    task_id : int
        ID of the task that uses the database
    database : str
        Label or handle of the database
    type : str
        Type of the database (e.g. source or handle)

    """

    # fields
    task_id = Column("task_id", Integer, ForeignKey("task.id"))
    database = Column(String)
    type_ = Column("type", String)

    # relationships
    task = relationship("Task", back_populates="databases")
