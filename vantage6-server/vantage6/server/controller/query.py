"""Temporary file for storing queries that were in the DB-models"""

from vantage6.server.model import (
    Node,
    Collaboration,
    Task,
    Organization
)
from vantage6.server.model.base import DatabaseSessionManager


def tasks(self, collaboration: Collaboration, organization: Organization):
    """A node belongs to a single collaboration. Therefore the node
    only executes task for the organization and collaboration  is
    belongs to.

    Tasks can be assigned to many nodes but are only assigned to
    as single collaboration.
    """

    # find node of the organization that is within the collaboration
    node = collaboration.get_node_from_organization(organization)

    session = DatabaseSessionManager.get_session()
    tasks = session.query(Task)\
        .join(Collaboration)\
        .join(Node)\
        .filter_by(collabotation_id=collaboration.id)\
        .filter(Node == node.id)\
        .all()

    return tasks
