from enum import Enum

from vantage6.server.model.rule import Operation, Scope


class DefaultRole(str, Enum):
    """ Enum containing the names of the default roles """
    DEVELOPER = "Developer"
    ROOT = "Root"
    REVIEWER = "Reviewer"
    STORE_MANAGER = "Store Manager"
    VIEWER = "Viewer"


# TODO BvB 22-06-07: we now have to pass this 'db' module as argument to a
# function because that module has a connection to the database. This should
# not be necessary. Fix that after fixing the circular imports described in
# https://github.com/vantage6/vantage6/issues/53
def get_default_roles(db) -> list[dict]:
    """
    Get a list containing the default roles and their rules, so that they may
    be created in the database

    Parameters
    ----------
    db
        The vantage6.server.db module

    Returns
    -------
    List[Dict]
        A list with dictionaries that each describe one of the roles. Each role
        dictionary contains the following:

        name: str
            Name of the role
        description: str
            Description of the role
        rules: List[int]
            A list of rule id's that the role contains
    """
    # Define default roles
    # 1. Root user
    SUPER_ROLE = {
        'name': DefaultRole.ROOT,
        'description': "Super role",
        # 'rules': db.Rule.get()
    }
    # 2. Role for viewing algorithms
    VIEWER_RULES = [
        # db.Rule.get_by_('user', Scope.OWN, Operation.EDIT),
        # db.Rule.get_by_('user', Scope.OWN, Operation.DELETE),
        # db.Rule.get_by_('user', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('organization', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('organization', Scope.COLLABORATION, Operation.VIEW),
        # db.Rule.get_by_('collaboration', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('role', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('node', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('node', Scope.COLLABORATION, Operation.VIEW),
        # db.Rule.get_by_('task', Scope.COLLABORATION, Operation.VIEW),
        # db.Rule.get_by_('run', Scope.COLLABORATION, Operation.VIEW),
        # db.Rule.get_by_('port', Scope.ORGANIZATION, Operation.VIEW),
        # db.Rule.get_by_('event', Scope.ORGANIZATION, Operation.RECEIVE),
    ]
    VIEWER_ROLE = {
        'name': DefaultRole.VIEWER,
        'description': "Can manage their own account and view algorithms",
        'rules': VIEWER_RULES
    }
    # 3. Reviewer role
    REVIEWER_RULES = []
    REVIEWER_ROLE = {
        'name': DefaultRole.REVIEWER,
        'description': "Can view and edit algorithms",
        'rules': REVIEWER_RULES
    }
    # 4. Store manager role
    STORE_MANAGER = []
    STORE_MANAGER = {
        'name': DefaultRole.STORE_MANAGER,
        'description':
            "Can view and delete algorithms.",
        'rules': STORE_MANAGER
    }
    # 4. Developer role
    DEVELOPER_RULES = []
    DEVELOPER_ROLE = {
        'name': DefaultRole.DEVELOPER,
        'description':
            "Can view and create algorithms.",
        'rules': STORE_MANAGER
    }
    # Combine all in array
    return [
        SUPER_ROLE, VIEWER_ROLE, REVIEWER_ROLE, STORE_MANAGER,
        DEVELOPER_ROLE
    ]
