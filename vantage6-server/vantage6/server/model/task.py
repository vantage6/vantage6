from typing import List
from sqlalchemy import Column, String, ForeignKey, Integer, sql
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.server.model.node import Node
from vantage6.server.model.base import Base, DatabaseSessionManager


class Task(Base):
    """
    Table that describes all tasks.

    A task can contain multiple Results for multiple organizations. The input
    of the task is different for each organization (due to the encryption).
    Therefore the input for the task is encrypted for each organization
    separately. The task originates from an organization to which the results
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
    initiator_id : int
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
    run_id = Column(Integer)
    parent_id = Column(Integer, ForeignKey("task.id"))
    database = Column(String)
    initiator_id = Column(Integer, ForeignKey("organization.id"))
    init_user_id = Column(Integer, ForeignKey("user.id"))

    # relationships
    collaboration = relationship("Collaboration", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="children")
    results = relationship("Result", back_populates="task")
    # TODO in v4, rename the 'initiator' column so that there is a clear
    # distinction between initiating organization and user
    initiator = relationship("Organization", back_populates="created_tasks")
    init_user = relationship("User", back_populates="created_tasks")

    # TODO remove this property in v4. It is superseded by status but now left
    # here for backwards compatibility with other v3 versions
    @hybrid_property
    def complete(self) -> bool:
        """
        Determine if a task is complete, i.e. whether all underlying results
        are complete.

        Returns
        -------
        bool
            True if task is complete, False otherwise
        """
        return all([r.complete for r in self.results])

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
        result_statuses = [r.status for r in self.results]
        if all([status is None for status in result_statuses]):
            # TODO remove in v4 (this is for backwards compatibility because
            # task statuses where not present in <3.6)
            return 'unknown'
        elif any([has_task_failed(status) for status in result_statuses]):
            return TaskStatus.FAILED.value
        elif TaskStatus.ACTIVE in result_statuses:
            return TaskStatus.ACTIVE.value
        elif TaskStatus.INITIALIZING in result_statuses:
            return TaskStatus.INITIALIZING.value
        elif TaskStatus.PENDING in result_statuses:
            return TaskStatus.PENDING.value
        else:
            return TaskStatus.COMPLETED.value

    def results_for_node(self, node: Node) -> List:
        """
        Get all results for a given node.

        Parameters
        ----------
        node: model.node.Node
            Node for which to get the results

        Returns
        -------
        List[model.result.Result]
            List of results for the given node
        """
        assert isinstance(node, Node), "Should be a node..."
        return [result for result in self.results if
                self.collaboration == node.collaboration and
                self.organization == node.organization]

    @classmethod
    def next_run_id(cls) -> int:
        """
        Get the next available run id for a new task.

        Returns
        -------
        int
            Next available run id
        """
        session = DatabaseSessionManager.get_session()
        max_run_id = session.query(sql.func.max(cls.run_id)).scalar()
        session.commit()
        if max_run_id:
            return max_run_id + 1
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
