import datetime
import logging

from sqlalchemy import Column, Text, DateTime, Integer, ForeignKey, select
from sqlalchemy.orm import relationship, validates
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

from vantage6.common import logger_name
from vantage6.server.model.base import Base, DatabaseSessionManager
from vantage6.common.enum import AlgorithmStepType
from vantage6.server.model import Node, Collaboration, Organization
from vantage6.server.model.task import Task

log_ = logging.getLogger(logger_name(__name__))


class Run(Base):
    """
    A Run is the description of a :class:`.~vantage6.server.model.task.Task` as
    executed by a Node.

    The arguments and result fields will be encrypted and can be only read by the
    intended receiver of the message.

    Attributes
    ----------
    arguments : str
        Function arguments to call the algorithm function with. The arguments are
        encoded, and depending on the collaboration-level settings, also encrypted
        for the organization that is executing the task.
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
    cleanup_at : datetime
        Time when the results were deleted as part of a cleanup
    status : str
        Status of the task
    log : str
        Log of the task
    action : :class:`.~vantage6.common.AlgorithmStepType`
        Action type of the task

    Relationships
    -------------
    task : :class:`.~vantage6.server.model.task.Task`
        Task that was executed
    organization : :class:`.~vantage6.server.model.organization.Organization`
        Organization that executed the task
    """

    # fields
    arguments = Column(Text)
    task_id = Column(Integer, ForeignKey("task.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))
    result = Column(Text)
    assigned_at = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    status = Column(Text)
    log = Column(Text)
    action = Column(Text)
    cleanup_at = Column(DateTime, nullable=True)

    # relationships
    task = relationship("Task", back_populates="runs")
    organization = relationship("Organization", back_populates="runs")

    @validates("action")
    def validate_action(self, _, action):
        """
        Validate the action field.

        Parameters
        ----------
        action : str
            The action to validate

        Returns
        -------
        str
            The validated action

        Raises
        ------
        ValueError
            If the action is not a valid AlgorithmStepType
        """
        if action not in AlgorithmStepType.list():
            raise ValueError(f"Invalid action: {action}")
        return action

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
            node = session.scalars(
                select(Node)
                .join(Collaboration)
                .join(Organization)
                .join(Run)
                .join(Task)
                .filter(Run.id == self.id)
                .filter(self.organization_id == Node.organization_id)
                .filter(Task.collaboration_id == Node.collaboration_id)
            ).one()
            session.commit()
        # FIXME 2022-03-03 BvB: the following errors are not currently
        # forwarded to the user as request response. Make that happen.
        except NoResultFound:
            log_.warning(
                "No node exists for organization_id %s in the current collaboration!",
                self.organization_id,
            )
            return None
        except MultipleResultsFound:
            log_.error(
                "Multiple nodes are registered for organization_id %s in the current "
                "collaboration. Please delete all nodes but one.",
                self.organization_id,
            )
            raise
        return node

    def __repr__(self) -> str:
        """
        Returns a string representation of the result.

        Returns
        -------
        str
            String representation of the result.
        """
        return (
            "<Run "
            f"{self.id}: '{self.task.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.task.collaboration.name}, "
            f"status: {self.status}"
            ">"
        )
