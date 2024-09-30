import datetime

import vantage6.server.model as models

from sqlalchemy import (
    Column,
    String,
    ForeignKey,
    Integer,
    sql,
    DateTime,
    select,
    func,
    case,
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common.enum import TaskStatus, RunStatus
from vantage6.server.model.base import Base, DatabaseSessionManager


class Task(Base):
    """
    Table that describes all tasks.

    A single Task can create algorithm Runs for multiple organizations.

    A task always belongs to a session and collaboration. Optionally it can be assigned
    to a study. A task can have a parent task or can depend on other tasks. A task can
    have multiple runs and results. A single task can require multiple datasets to be
    provided.

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
    dataframe_id : int
        Id of the dataframe that this task manipulates
    job_id : int
        Id of the job that this task belongs to
    parent_id : int
        Id of the parent task (if any)
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
    depends_on : list[:class:`~.model.task.Task`]
        List of tasks that this task depends on
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
    dataframe : :class:`~.model.dataframe.Dataframe`
        Dataframe that is manipulated by this task, only tasks that modify the
        session dataframe will have this field filled in
    """

    # fields
    name = Column(String)
    description = Column(String)
    image = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    study_id = Column(Integer, ForeignKey("study.id"))
    session_id = Column(Integer, ForeignKey("session.id"))
    dataframe_id = Column(Integer, ForeignKey("dataframe.id"))
    job_id = Column(Integer)
    parent_id = Column(Integer, ForeignKey("task.id"))
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
        backref="required_by",
        secondary="task_depends_on",
        primaryjoin="Task.id==task_depends_on.c.task_id",
        secondaryjoin="Task.id==task_depends_on.c.depends_on_id",
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
    dataframe = relationship(
        "Dataframe", back_populates="tasks", foreign_keys=[dataframe_id]
    )

    # TODO FM 26-07-2024: Clean up these action methods. Use the same LocalAction enums
    @hybrid_property
    def action(self) -> str:
        """
        Determine the action that needs to be taken by the algorithm container
        for this task.

        Returns
        -------
        str
            Action that needs to be taken by the algorithm container
        """
        return "compute" if not self.dataframe_id else "preprocess"

    @action.expression
    def action(cls):
        """
        SQL expression for the action hybrid property.
        """
        return case([(cls.dataframe_id.is_(None), "compute")], else_="preprocess")

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
        run_statuses = [r.status for r in self.runs]
        if all([RunStatus.has_finished(status) for status in run_statuses]):
            return TaskStatus.COMPLETED.value
        elif any([RunStatus.has_failed(status) for status in run_statuses]):
            return TaskStatus.FAILED.value
        else:
            return TaskStatus.AWAITING.value

    @status.expression
    def status(cls):

        failed_case = case(
            [(models.Run.status.in_(RunStatus.failed_statuses()), 1)],
            else_=0,
        )

        alive_case = case(
            [(models.Run.status.in_(RunStatus.alive_statuses()), 1)],
            else_=0,
        )

        status_case = case(
            [
                (func.sum(failed_case) > 0, TaskStatus.FAILED.value),
                (func.sum(alive_case) > 0, TaskStatus.AWAITING.value),
            ],
            else_=TaskStatus.COMPLETED.value,
        )

        return select([status_case]).where(models.Run.task_id == cls.id).label("status")

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
            f"status: {self.status}, "
            f"collaboration:{self.collaboration.name}, "
            f"action:{self.action}, "
            ">"
        )
