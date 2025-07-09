from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.server.model.base import Base


class TaskDatabase(Base):
    """
    Table to store which databases are used by which tasks.

    Each record contains a database label or dataframe ID to refer to a database that
    will be used for a task with ID ``task_id``. Each task will usually have zero, one
    or multiple databases assigned to it.

    Typically *data extraction* tasks will have a database label, while
    *pre-processing* and *compute* tasks will have one or more linked dataframes.

    Attributes
    ----------
    task_id : int
        ID of the task that uses the database
    label : str
        Database label. Only specified for data extraction steps.
    dataframe_id : int
        ID of the dataframe used as database. Specified for all task types except
        data extraction.
    type_ : str
        Type of the database (e.g. source or dataframe)
    position : int
        Position of the database in the argument list supplied to the algorithm, as
        specified by the user.

    Relationships
    -------------
    task : :class:`~vantage6.server.model.task.Task`
        Task that uses the database
    """

    # fields
    task_id = Column("task_id", Integer, ForeignKey("task.id"))
    label = Column(String)
    dataframe_id = Column(Integer, ForeignKey("dataframe.id"))
    type_ = Column("type", String)
    position = Column(Integer)

    # relationships
    task = relationship("Task", back_populates="databases")
    dataframe = relationship("Dataframe", back_populates="task_databases")
