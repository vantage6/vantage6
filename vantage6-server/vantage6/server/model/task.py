import datetime
import os

from sqlalchemy import Column, String, ForeignKey, Integer, sql, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.server.model.base import Base, DatabaseSessionManager


class Task(Base):
    """
    Table that describes all tasks.

    A Task can create algorithm Runs for multiple organizations. The input
    of the task is different for each organization (due to the encryption).
    Therefore the input for the task is encrypted for each organization
    separately. The task originates from an organization to which the Runs
    need to be encrypted, therefore the originating organization is also logged

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

    collaboration : :class:`~.model.collaboration.Collaboration`
        Collaboration that this task belongs to
    parent : :class:`~.model.task.Task`
        Parent task (if any)
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
    """

    # fields
    name = Column(String)
    description = Column(String)
    image = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    study_id = Column(Integer, ForeignKey("study.id"))
    job_id = Column(Integer)
    parent_id = Column(Integer, ForeignKey("task.id"))
    init_org_id = Column(Integer, ForeignKey("organization.id"))
    init_user_id = Column(Integer, ForeignKey("user.id"))
    created_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    algorithm_store_id = Column(Integer, ForeignKey("algorithmstore.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="children")
    runs = relationship("Run", back_populates="task")
    # This second relationship is needed when constructing output JSON (
    # including results with the task). It is marked 'view_only' to prevent
    # write conflicts with the runs relationship.
    results = relationship("Run", back_populates="task", viewonly=True)
    init_org = relationship("Organization", back_populates="tasks")
    init_user = relationship("User", back_populates="created_tasks")
    databases = relationship("TaskDatabase", back_populates="task")
    study = relationship("Study", back_populates="tasks")
    algorithm_store = relationship("AlgorithmStore", back_populates="tasks")

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
            if self.status == TaskStatus.COMPLETED.value and self.results
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
            # check if all runs that have failed have failed for the same reason - if
            # so, return that reason. If not, return generic failed status
            failed_runs = [r for r in self.runs if has_task_failed(r.status)]
            if len(set([r.status for r in failed_runs])) == 1:
                return failed_runs[0].status
            else:
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
