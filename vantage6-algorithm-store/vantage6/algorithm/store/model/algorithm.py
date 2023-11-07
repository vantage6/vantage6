from __future__ import annotations
from sqlalchemy import Column, String

from vantage6.algorithm.store.model.base import Base


class Algorithm(Base):
    """
    Table that describes which collaborations are available.

    Collaborations are combinations of one or more organizations
    that do studies together. Each
    :class:`~vantage6.server.model.organization.Organization` has a
    :class:`~vantage6.server.model.node.Node` for
    each collaboration that it is part of. Within a collaboration multiple
    :class:`~vantage6.server.model.task.Task` can be executed.

    Attributes
    ----------
    name : str
        Name of the collaboration
    encrypted : bool
        Whether the collaboration is encrypted or not
    organizations :
            list[:class:`~vantage6.server.model.organization.Organization`]
        List of organizations that are part of this collaboration
    nodes : list[:class:`~vantage6.server.model.node.Node`]
        List of nodes that are part of this collaboration
    tasks : list[:class:`~vantage6.server.model.task.Task`]
        List of tasks that are part of this collaboration
    """

    # fields
    name = Column(String, unique=True)

    # relationships
    # functions = relationship("Function", back_populates='algorithms')


