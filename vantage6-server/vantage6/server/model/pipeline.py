from typing import TYPE_CHECKING

from sqlalchemy import Column, Integer, ForeignKey, String
from sqlalchemy.orm import relationship

# from vantage6.server.model.
from vantage6.server.model.base import Base, DatabaseSessionManager

if TYPE_CHECKING:
    from vantage6.server.model import Session


class Pipeline(Base):
    """
    Table to store session configuration by key-value pairs.

    This information includes e.g. which database handles are available to use.

    Attributes
    ----------
    handle : str
        User handle to reference this pipeline
    session_id : int
        ID of the session that this pipeline belongs to
    last_session_task_id : int
        ID of the last task that alters this session.

    Relationships
    -------------
    session : :class:`~.model.Session.Session`
        Session that this configuration belongs to
    tasks : list of :class:`~.model.Task.Task`
        Tasks that build the session data frame. In other words ``compute`` tasks that
        are executed in the session are not included.

    """

    # fields
    handle = Column(String)
    session_id = Column(Integer, ForeignKey("session.id"))
    last_session_task_id = Column(Integer, ForeignKey("task.id"))

    # relationships
    session = relationship("Session", back_populates="pipelines")
    tasks = relationship(
        "Task", back_populates="pipeline", foreign_keys="Task.pipeline_id"
    )
    last_session_task = relationship("Task", foreign_keys=[last_session_task_id])

    @classmethod
    def select(cls, session: "Session", handle: str):
        """
        Select a pipeline by session and handle.

        Parameters
        ----------
        session : :class:`~.model.Session.Session`
            Session to which the pipeline belongs
        handle : str
            Handle of the pipeline

        Returns
        -------
        :class:`~.model.Pipeline.Pipeline` | None
            Pipeline that corresponds to the given session and handle
        """
        db_session = DatabaseSessionManager.get_session()
        pipeline = (
            db_session.query(cls)
            .filter_by(session_id=session.id, handle=handle)
            .first()
        )
        db_session.commit()
        return pipeline

    def __repr__(self):
        return f"<Pipeline {self.handle}>"
