import datetime
import os

from sqlalchemy import Column, String, ForeignKey, Integer, sql, DateTime
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.server.model.base import Base, DatabaseSessionManager


class Task(Base):
    """
    Table that describes all tasks.

    A single Task can create algorithm Runs for multiple organizations.

    A task always belongs to a session and collaboration. Optionally it can be assigned
    to a study. A task can have a parent task or can depend on other tasks. A task can
    have multiple runs and results. A single task can require multiple datasets to be
    profided.

    Each Task is associated with a specific session and collaboration. It can optionally
    be assigned to a study.

    A Task can have a parent task or can depend on other tasks. It can also have
    multiple runs and results.

    The input for each Task differs per organization due to encryption, in other words
    each Task's input is encrypted separately for each organization.

    A single Task may require multiple datasets to be provided.

    Attributes
    ----------
    name : str
        Name of the task
    description : str
        Description of the task
    image : str
        Name of the docker image that needs to be executed
    collaboration_id : int
        Id of the collaboration that this task belongs to
    study_id : int
        Id of the study that this task belongs to
    session_id : int
        Id of the session that this task belongs to
    job_id : int
        Id of the job that this task belongs to
    parent_id : int
        Id of the parent task (if any)
    depends_on_id : int
        Id of the task that this task depends on
    init_org_id : int
        Id of the organization that created this task
    init_user_id : int
        Id of the user that created this task
    created_at : datetime.datetime
        Time at which this task was created
    algorithm_store_id : int
        Id of the algorithm store that this task belongs to

    Relationships
    -------------
    collaboration : :class:`~.model.collaboration.Collaboration`
        Collaboration that this task belongs to
    parent : :class:`~.model.task.Task`
        Parent task (if any)
    children : list[:class:`~.model.task.Task`]
        List of child tasks
    depends_on : :class:`~.model.task.Task`
        Task that this task depends on
    required_by : list[:class:`~.model.task.Task`]
        List of tasks that depend on this task
    runs : list[:class:`~.model.run.Run`]
        List of runs that are part of this task
    results : list[:class:`~.model.result.Result`]
        List of results that are part of this task
    init_org : :class:`~.model.organization.Organization`
        Organization that created this task
    init_user : :class:`~.model.user.User`
        User that created this task
    databases : list[:class:`~.model.task_database.TaskDatabase`]
        List of databases that are part of this task
    study : :class:`~.model.study.Study`
        Study that this task belongs to
    algorithm_store : :class:`~.model.algorithm_store.AlgorithmStore`
        Algorithm store that this task uses
    session : :class:`~.model.session.Session`
        Session that this task belongs to
    """

    # fields
    name = Column(String)
    description = Column(String)
    image = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    study_id = Column(Integer, ForeignKey("study.id"))
    session_id = Column(Integer, ForeignKey("session.id"))
    job_id = Column(Integer)
    parent_id = Column(Integer, ForeignKey("task.id"))
    depends_on_id = Column(Integer, ForeignKey("task.id"))
    init_org_id = Column(Integer, ForeignKey("organization.id"))
    init_user_id = Column(Integer, ForeignKey("user.id"))
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    algorithm_store_id = Column(Integer, ForeignKey("algorithmstore.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="tasks")
    parent = relationship(
        "Task",
        remote_side="Task.id",
        foreign_keys=[parent_id],
        backref=backref("children"),
    )
    depends_on = relationship(
        "Task",
        remote_side="Task.id",
        foreign_keys=[depends_on_id],
        backref=backref("required_by"),
    )
    runs = relationship("Run", back_populates="task")
    # This second `Run` relationship is needed when constructing output JSON (
    # including results with the task). It is marked 'view_only' to prevent write
    # conflicts with the runs relationship.
    results = relationship("Run", back_populates="task", viewonly=True)
    init_org = relationship("Organization", back_populates="tasks")
    init_user = relationship("User", back_populates="created_tasks")
    databases = relationship("TaskDatabase", back_populates="task")
    study = relationship("Study", back_populates="tasks")
    algorithm_store = relationship("AlgorithmStore", back_populates="tasks")
    session = relationship("Session", back_populates="tasks")

    # TODO update in v4+, with renaming to 'run'
    @hybrid_property
    def finished_at(self) -> datetime.datetime | None:
        """
        Determine the time at which a task was completed. This is the time at
        which the last algorithm run was completed.

        Returns
        -------
        datetime.datetime | None
            Time at which task was completed, None if task is not completed
        """
        return (
            max([r.finished_at for r in self.results])
            if self.complete and self.results
            else None
        )

    @hybrid_property
    def status(self) -> str:
        """
        Returns the status of a task, which is derived from the statuses of
        the underlying algorithm runs.

        Returns
        -------
        str
            Status of task
        """
        # The following is necessary because if readthedocs executes this code to
        # generate function docs, it will fail with a sqlalchemy error (because there
        # are no runs?).
        if os.environ.get("READTHEDOCS"):
            return ""
        # TODO what if there are no result ids? -> currently returns unknown
        run_statuses = [r.status for r in self.runs]
        if any([has_task_failed(status) for status in run_statuses]):
            return TaskStatus.FAILED.value
        elif TaskStatus.ACTIVE in run_statuses:
            return TaskStatus.ACTIVE.value
        elif TaskStatus.INITIALIZING in run_statuses:
            return TaskStatus.INITIALIZING.value
        elif TaskStatus.PENDING in run_statuses:
            return TaskStatus.PENDING.value
        else:
            return TaskStatus.COMPLETED.value

    @classmethod
    def next_job_id(cls) -> int:
        """
        Get the next available run id for a new task.

        Returns
        -------
        int
            Next available run id
        """
        session = DatabaseSessionManager.get_session()
        max_job_id = session.query(sql.func.max(cls.job_id)).scalar()
        session.commit()
        if max_job_id:
            return max_job_id + 1
        else:
            return 1

    def __repr__(self) -> str:
        """
        String representation of the Task object

        Returns
        -------
        str
            String representation of the Task object
        """
        return (
            f"<Task "
            f"{self.id}: '{self.name}', "
            f"collaboration:{self.collaboration.name}"
            ">"
        )
