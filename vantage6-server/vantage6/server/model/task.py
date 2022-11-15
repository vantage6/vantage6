from sqlalchemy import Column, String, ForeignKey, Integer, sql
from sqlalchemy.orm import relationship
from sqlalchemy.ext.hybrid import hybrid_property

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

    # relationships
    collaboration = relationship("Collaboration", back_populates="tasks")
    parent = relationship("Task", remote_side="Task.id", backref="children")
    results = relationship("Result", back_populates="task")
    initiator = relationship("Organization", back_populates="created_tasks")

    @hybrid_property
    def complete(self):
        return all([r.complete for r in self.results])

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
