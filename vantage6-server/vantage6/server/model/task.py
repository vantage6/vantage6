from sqlalchemy import Column, String, ForeignKey, Integer, sql
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common.task_status import TaskStatus, has_task_failed
from vantage6.server.model.node import Node
from vantage6.server.model.base import Base, DatabaseSessionManager


class Task(Base):
    """Central definition of a single task.

    A task can assigned in the Result for multiple organizations. The input
    of the task is different for each organization (due to the encryption).
    Therefore the input for the task is encrypted for each organization
    separately. The task originates from an organization to which the results
    need to be encrypted, therefore the originating organization is also logged
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
    def complete(self):
        return all([r.complete for r in self.results])

    @hybrid_property
    def status(self) -> str:
        """
        Determine the status of a task by

        Returns
        -------
        str:
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

    def results_for_node(self, node):
        assert isinstance(node, Node), "Should be a node..."
        return [result for result in self.results if
                self.collaboration == node.collaboration and
                self.organization == node.organization]

    @classmethod
    def next_run_id(cls):
        session = DatabaseSessionManager.get_session()
        max_run_id = session.query(sql.func.max(cls.run_id)).scalar()
        if max_run_id:
            return max_run_id + 1
        else:
            return 1

    def __repr__(self):
        return (
            f"<Task "
            f"{self.id}: '{self.name}', "
            f"collaboration:{self.collaboration.name}"
            ">"
        )
