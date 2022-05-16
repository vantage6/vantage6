"""Temporary file for storing queries that were in the DB-models"""

from vantage6.server.model import (
    Node,
    Collaboration,
    Task,
    Organization,
    Result
)
from vantage6.server.model.base import DatabaseSessionManager


def get_node(self, result: Result):
    """A node is assigned by an organization to an collaboration.
    Tasks, that is responsible for a set of Results, are assigned
    to these collaborations.

    A Result is therefore directly related to a single node by it's
    organization and collaboration. Organization can be directly
    derived from the Result while the collaboration can be found from
    the originating task.
    """
    session = DatabaseSessionManager.get_session()
    node = session.query(Node)\
        .join(Collaboration)\
        .join(Task)\
        .join(Organization)\
        .join(Result)\
        .filter_by(result_id=result.id)\
        .filter(Task.organization_id == Node.organization_id)\
        .filter(Task.collaboration_id == Node.collaboration_id)\
        .one()

    return node


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
