import datetime
import logging

from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from sqlalchemy.ext.hybrid import hybrid_property

from vantage6.common import logger_name
from vantage6.server.model.base import Base
from vantage6.server.model import (
    Node,
    Collaboration,
    Organization
)
from vantage6.server.model.task import Task
from vantage6.server.model.base import DatabaseSessionManager

log_ = logging.getLogger(logger_name(__name__))


class Result(Base):
    """
    Table that describes which results are available. A Result is the
    description of a Task as executed by a Node.

    The result (and the input) is encrypted and can be only read by the
    intended receiver of the message.

    Attributes
    ----------
    input : str
        Input data of the task
    task_id : int
        Id of the task that was executed
    organization_id : int
        Id of the organization that executed the task
    result : str
        Result of the task
    assigned_at : datetime
        Time when the task was assigned to the node
    started_at : datetime
        Time when the task was started
    finished_at : datetime
        Time when the task was finished
    status : str
        Status of the task
    log : str
        Log of the task
    task : Task
        Task that was executed
    organization : Organization
        Organization that executed the task
    ports : list[AlgorithmPort]
        List of ports that are part of this result
    """

    # fields
    input = Column(Text)
    task_id = Column(Integer, ForeignKey("task.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))
    result = Column(Text)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    status = Column(Text)
    log = Column(Text)

    # relationships
    task = relationship("Task", back_populates="results")
    organization = relationship("Organization", back_populates="results")
    ports = relationship("AlgorithmPort", back_populates="result")

    @property
    def node(self) -> Node:
        """
        Returns the node that is associated with this result.

        Returns
        -------
        model.node.Node
            The node that is associated with this result.
        """
        session = DatabaseSessionManager.get_session()
        try:
            node = session.query(Node)\
                .join(Collaboration)\
                .join(Organization)\
                .join(Result)\
                .join(Task)\
                .filter(Result.id == self.id)\
                .filter(self.organization_id == Node.organization_id)\
                .filter(Task.collaboration_id == Node.collaboration_id)\
                .one()
            session.commit()
        # FIXME 2022-03-03 BvB: the following errors are not currently
        # forwarded to the user as request response. Make that happen.
        except NoResultFound:
            log_.warn("No node exists for organization_id "
                      f"{self.organization_id} in the current collaboration!")
            return None
        except MultipleResultsFound:
            log_.error("Multiple nodes are registered for organization_id "
                       f"{self.organization_id} in the current collaboration. "
                       "Please delete all nodes but one.")
            raise
        return node

    @hybrid_property
    def complete(self) -> bool:
        """
        Returns whether the algorithm run has completed or not.

        Returns
        -------
        bool
            True if the algorithm run has completed, False otherwise.
        """
        return self.finished_at is not None

    def __repr__(self) -> str:
        """
        Returns a string representation of the result.

        Returns
        -------
        str
            String representation of the result.
        """
        return (
            "<Result "
            f"{self.id}: '{self.task.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.task.collaboration.name}, "
            f"is_complete: {self.complete}"
            ">"
        )
