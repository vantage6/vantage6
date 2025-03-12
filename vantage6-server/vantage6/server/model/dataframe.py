from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String, select
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from vantage6.common.enum import RunStatus, TaskStatus, AlgorithmStepType
import vantage6.server.model as models
from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model import Session


class Dataframe(Base):
    """
    Table to store session configuration by key-value pairs.

    This information includes e.g. which database names are available to use.

    Attributes
    ----------
    name : str
        Dataframe name
    db_label: str
        Label of the database used to generate this dataframe
    session_id : int
        ID of the session that this dataframe belongs to
    last_session_task_id : int
        ID of the last task that alters this session (i.e. a data extraction or
        preprocessing task).

    Relationships
    -------------
    session : :class:`~.model.Session.Session`
        Session that this configuration belongs to
    tasks : list of :class:`~.model.Task.Task`
        Tasks that build the session dataframe. This implies that ``compute`` tasks
        executed in the session are not included.
    columns : list of :class:`~.model.Column.Column`
        Columns that are part of this dataframe
    last_session_task : :class:`~.model.Task.Task`
        Last task that alters this dataframe
    """

    # fields
    name = Column(String)
    db_label = Column(String)
    session_id = Column(Integer, ForeignKey("session.id"))
    last_session_task_id = Column(Integer, ForeignKey("task.id", use_alter=True))

    # relationships
    session = relationship("Session", back_populates="dataframes")
    tasks = relationship(
        "Task", back_populates="dataframe", foreign_keys="Task.dataframe_id"
    )
    columns = relationship("Column", back_populates="dataframe")
    last_session_task = relationship("Task", foreign_keys=[last_session_task_id])
    task_databases = relationship("TaskDatabase", back_populates="dataframe")

    def ready(self) -> bool:
        """
        Check if the dataframe is not being modified. The dataframe is considered to be
        ready if there are no session tasks running that can modify this dataframe.

        Returns
        -------
        bool
            True if the dataframe has no alive modifying tasks, False otherwise
        """
        # In case there are no tasks, the dataframe is not ready as there is no
        # dataframe constructed yet.
        if not self.last_session_task:
            return False

        # Since all session tasks are ran sequentially, we can check if the last task
        # is finished to determine if the dataframe is ready. Note that we do not care
        # wether the task completed successfully or not as we are only interested to
        # know wether a dataframe modification is in progress.
        return all(
            [RunStatus.has_finished(run.status) for run in self.last_session_task.runs]
        )

    @hybrid_property
    def active_compute_tasks(self) -> list[models.Task]:
        """
        Get all *compute* tasks that are not finished on this dataframe.

        Returns
        -------
        list[:class:`~.model.Task.Task`]
            List of compute tasks that are currently active on this dataframe
        """
        db_session = DatabaseSessionManager.get_session()
        active_compute_tasks = db_session.scalars(
            select(models.Task)
            .join(models.TaskDatabase)
            .filter(models.Task.action == AlgorithmStepType.COMPUTE.value)
            .filter(models.Task.status == TaskStatus.WAITING.value)
            .filter(models.TaskDatabase.dataframe_id == self.id)
            .filter(models.Task.session_id == self.session_id)
        ).all()
        db_session.commit()
        return active_compute_tasks

    def __repr__(self):
        return (
            f"<Dataframe {self.name}, session: {self.session.name}, "
            f"db: {self.db_label}>"
        )
