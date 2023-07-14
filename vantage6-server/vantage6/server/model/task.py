from sqlalchemy import Column, String, ForeignKey, Integer, sql
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
    run_id : int
        Run id of the task
    parent_id : int
        Id of the parent task (if any)
    database : str
        Name of the database that needs to be used for this task
    init_org_id : int
        Id of the organization that created this task
    init_user_id : int
        Id of the user that created this task

    collaboration : :class:`~.model.collaboration.Collaboration`
        Collaboration that this task belongs to
    parent : :class:`~.model.task.Task`
        Parent task (if any)
    results : list[:class:`~.model.result.Result`]
        List of results that are part of this task
    initiator : :class:`~.model.organization.Organization`
        Organization that created this task
    init_user : :class:`~.model.user.User`
        User that created this task

    """
    # fields
    name = Column(String)
    description = Column(String)
    image = Column(String)
    collaboration_id = Column(Integer, ForeignKey("collaboration.id"))
    job_id = Column(Integer)
    parent_id = Column(Integer, ForeignKey("task.id"))
    init_org_id = Column(Integer, ForeignKey("organization.id"))
    init_user_id = Column(Integer, ForeignKey("user.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="children")
    runs = relationship("Run", back_populates="task")
    init_org = relationship("Organization", back_populates="tasks")
    init_user = relationship("User", back_populates="created_tasks")
    databases = relationship("TaskDatabase", back_populates="task")

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
