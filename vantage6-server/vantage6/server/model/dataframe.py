from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

from vantage6.common.enums import TaskStatus
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
        Tasks that build the session data frame. In other words ``compute`` tasks that
        are executed in the session are not included.
    columns : list of :class:`~.model.Column.Column`
        Columns that are part of this dataframe
    last_session_task : :class:`~.model.Task.Task`
        Last task that alters this session
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

    def ready(self) -> bool:
        """
        Check if the dataframe is ready to receive computation tasks. The dataframe is
        considered to be ready if there are no session tasks running.

        Returns
        -------
        dict
            State of the dataframe
        """
        return self.last_session_task.status == TaskStatus.COMPLETED

    def locked(self) -> bool:
        """
        Check if the dataframe can be modified. The dataframe can only be modified if
        there are no session tasks running that can modify the dataframe data frame.

        Returns
        -------
        bool
            True if the dataframe is locked, False otherwise
        """

        db_session = DatabaseSessionManager.get_session()
        # TODO FM 17-07-2024: we cannot do this here, I dont want to have this import
        # here
        from vantage6.server.model import Task

        are_tasks_still_running = (
            db_session.query(Task)
            .filter(
                Task.dataframe_id == self.id,
                Task.status.in_(TaskStatus.alive_statuses()),
            )
            .limit(1)
            .scalar()
            is not None
        )

        db_session.commit()
        return are_tasks_still_running

    @classmethod
    def select(cls, session: "Session", handle: str):
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
        return f"<Dataframe {self.handle}>"
