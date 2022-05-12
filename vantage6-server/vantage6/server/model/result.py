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
    Task,
    Organization
)
from vantage6.server.model.base import DatabaseSessionManager

log_ = logging.getLogger(logger_name(__name__))


class Result(Base):
    """Result of a Task as executed by a Node.

    The result (and the input) is encrypted and can be only read by the
    intended receiver of the message.
    """

    # fields
    input = Column(Text)
    task_id = Column(Integer, ForeignKey("task.id"))
    organization_id = Column(Integer, ForeignKey("organization.id"))
    result = Column(Text)
    assigned_at = Column(DateTime, default=datetime.datetime.utcnow)
    started_at = Column(DateTime)
    finished_at = Column(DateTime)
    log = Column(Text)

    # relationships
    task = relationship("Task", back_populates="results")
    organization = relationship("Organization", back_populates="results")
    ports = relationship("AlgorithmPort", back_populates="result")

    @property
    def node(self):
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
    def complete(self):
        return self.finished_at is not None

    def __repr__(self):
        return (
            "<Result "
            f"{self.id}: '{self.task.name}', "
            f"organization: {self.organization.name}, "
            f"collaboration: {self.task.collaboration.name}, "
            f"is_complete: {self.complete}"
            ">"
        )
