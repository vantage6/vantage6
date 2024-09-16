import vantage6.server.model as models

from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String, and_, case
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from vantage6.common.enum import RunStatus, TaskStatus
from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model import Session


class Dataframe(Base):
    """
    Table to store session configuration by key-value pairs.

    This information includes e.g. which database handles are available to use.

    Attributes
    ----------
    handle : str
        User handle to reference this dataframe
    session_id : int
        ID of the session that this dataframe belongs to
    last_session_task_id : int
        ID of the last task that alters this session.

    Relationships
    -------------
    session : :class:`~.model.Session.Session`
        Session that this configuration belongs to
    tasks : list of :class:`~.model.Task.Task`
        Tasks that build the session data frame. This implies that ``compute`` tasks
        executed in the session are not included.
    columns : list of :class:`~.model.Column.Column`
        Columns that are part of this dataframe
    last_session_task : :class:`~.model.Task.Task`
        Last task that alters this dataframe
    """

    # fields
    handle = Column(String)
    session_id = Column(Integer, ForeignKey("session.id"))
    last_session_task_id = Column(Integer, ForeignKey("task.id"))

    # relationships
    session = relationship("Session", back_populates="dataframes")
    tasks = relationship(
        "Task", back_populates="dataframe", foreign_keys="Task.dataframe_id"
    )
    columns = relationship("Column", back_populates="dataframe")
    last_session_task = relationship("Task", foreign_keys=[last_session_task_id])

    @hybrid_property
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

    @ready.expression
    def ready(cls):
        return and_(
            cls.last_session_task != None,
            *[
                run.status.in_(RunStatus.dead_statuses())
                for run in cls.last_session_task.runs
            ],
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
        # TODO FM 26-07-2024: The compute should be coming from an enum
        db_session = DatabaseSessionManager.get_session()
        active_compute_tasks = (
            db_session.query(models.Task)
            .join(models.TaskDatabase)
            .filter(models.Task.action == "compute")
            .filter(models.Task.status == TaskStatus.AWAITING.value)
            .filter(models.TaskDatabase.database == self.handle)
            .filter(models.Task.session_id == self.session_id)
            .all()
        )
        db_session.commit()
        return active_compute_tasks

    @classmethod
    def select(cls, session: "Session", handle: str) -> "Dataframe":
        """
        Select a dataframe by session and handle.

        Parameters
        ----------
        session : :class:`~.model.Session.Session`
            Session to which the dataframe belongs
        handle : str
            Handle of the dataframe

        Returns
        -------
        :class:`~.model.Dataframe.Dataframe` | None
            Dataframe that corresponds to the given session and handle
        """
        db_session = DatabaseSessionManager.get_session()
        dataframe = (
            db_session.query(cls)
            .filter_by(session_id=session.id, handle=handle)
            .first()
        )
        db_session.commit()
        return dataframe

    def __repr__(self):
        return f"<Dataframe {self.handle}, " f"session: {self.session.name}>"
