from enum import Enum

from vantage6.server.model.rule import Operation, Scope


class DefaultRole(str, Enum):
    """Enum containing the names of the default roles"""

    ROOT = "Root"
    CONTAINER = "container"
    NODE = "node"
    VIEWER = "Viewer"
    RESEARCHER = "Researcher"
    ORG_ADMIN = "Organization Admin"
    COL_ADMIN = "Collaboration Admin"


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
        "name": DefaultRole.ROOT,
        "description": "Super role",
        "rules": db.Rule.get(),
        "is_default_role": True,
    }
    # 2. Role for viewing organization resources
    VIEWER_RULES = [
        db.Rule.get_by_("user", Scope.OWN, Operation.EDIT),
        db.Rule.get_by_("user", Scope.OWN, Operation.DELETE),
        db.Rule.get_by_("user", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("organization", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("organization", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("role", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("node", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("node", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("task", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("run", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("port", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("event", Scope.ORGANIZATION, Operation.RECEIVE),
        db.Rule.get_by_("event", Scope.COLLABORATION, Operation.RECEIVE),
        db.Rule.get_by_("study", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("session", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("session", Scope.COLLABORATION, Operation.VIEW),
    ]
    VIEWER_ROLE = {
        "name": DefaultRole.VIEWER,
        "description": "Can manage their own account and view resources "
        "related to their organization",
        "rules": VIEWER_RULES,
        "is_default_role": True,
    }
    # 3. Researcher role
    RESEARCHER_RULES = VIEWER_RULES + [
        db.Rule.get_by_("task", Scope.COLLABORATION, Operation.CREATE),
        db.Rule.get_by_("task", Scope.ORGANIZATION, Operation.DELETE),
        db.Rule.get_by_("session", Scope.OWN, Operation.CREATE),
        db.Rule.get_by_("session", Scope.ORGANIZATION, Operation.CREATE),
        db.Rule.get_by_("session", Scope.OWN, Operation.EDIT),
        db.Rule.get_by_("session", Scope.ORGANIZATION, Operation.EDIT),
        db.Rule.get_by_("session", Scope.OWN, Operation.DELETE),
        db.Rule.get_by_("session", Scope.ORGANIZATION, Operation.DELETE),
    ]
    RESEARCHER_ROLE = {
        "name": DefaultRole.RESEARCHER,
        "description": "Can perform tasks, manage their own account, and "
        "view resources related to their organization",
        "rules": RESEARCHER_RULES,
        "is_default_role": True,
    }
    # 4. Organization administrator role
    ORG_ADMIN_RULES = RESEARCHER_RULES + [
        db.Rule.get_by_("user", Scope.ORGANIZATION, Operation.CREATE),
        db.Rule.get_by_("user", Scope.ORGANIZATION, Operation.EDIT),
        db.Rule.get_by_("user", Scope.ORGANIZATION, Operation.DELETE),
        db.Rule.get_by_("organization", Scope.ORGANIZATION, Operation.EDIT),
        db.Rule.get_by_("role", Scope.ORGANIZATION, Operation.CREATE),
        db.Rule.get_by_("role", Scope.ORGANIZATION, Operation.EDIT),
        db.Rule.get_by_("role", Scope.ORGANIZATION, Operation.DELETE),
        db.Rule.get_by_("node", Scope.ORGANIZATION, Operation.CREATE),
        db.Rule.get_by_("node", Scope.ORGANIZATION, Operation.EDIT),
        db.Rule.get_by_("event", Scope.ORGANIZATION, Operation.SEND),
    ]
    ORG_ADMIN_ROLE = {
        "name": DefaultRole.ORG_ADMIN,
        "description": "Can manage an organization including its users, roles, and nodes."
        " Also has all permissions of a researcher.",
        "rules": ORG_ADMIN_RULES,
        "is_default_role": True,
    }
    # 4. Collaboration administrator role
    COLLAB_ADMIN_RULES = ORG_ADMIN_RULES + [
        db.Rule.get_by_("user", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("user", Scope.COLLABORATION, Operation.CREATE),
        db.Rule.get_by_("user", Scope.COLLABORATION, Operation.EDIT),
        # The following rule is given so that a collaboration admin can
        # view which organizations they may add to their collaboration
        db.Rule.get_by_("organization", Scope.GLOBAL, Operation.VIEW),
        db.Rule.get_by_("organization", Scope.COLLABORATION, Operation.EDIT),
        db.Rule.get_by_("collaboration", Scope.ORGANIZATION, Operation.VIEW),
        db.Rule.get_by_("collaboration", Scope.COLLABORATION, Operation.EDIT),
        db.Rule.get_by_("role", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("node", Scope.COLLABORATION, Operation.CREATE),
        db.Rule.get_by_("node", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("node", Scope.COLLABORATION, Operation.DELETE),
        db.Rule.get_by_("event", Scope.COLLABORATION, Operation.SEND),
        db.Rule.get_by_("study", Scope.COLLABORATION, Operation.VIEW),
        db.Rule.get_by_("study", Scope.COLLABORATION, Operation.CREATE),
        db.Rule.get_by_("study", Scope.COLLABORATION, Operation.EDIT),
        db.Rule.get_by_("study", Scope.COLLABORATION, Operation.DELETE),
        db.Rule.get_by_("session", Scope.COLLABORATION, Operation.CREATE),
        db.Rule.get_by_("session", Scope.COLLABORATION, Operation.EDIT),
        db.Rule.get_by_("session", Scope.COLLABORATION, Operation.DELETE),
    ]
    COLLAB_ADMIN_ROLE = {
        "name": DefaultRole.COL_ADMIN,
        "description": "Can manage an collaboration including its organization and users."
        " Also has permissions of an organization admin.",
        "rules": COLLAB_ADMIN_RULES,
        "is_default_role": True,
    }
    # Combine all in array
    return [SUPER_ROLE, VIEWER_ROLE, RESEARCHER_ROLE, ORG_ADMIN_ROLE, COLLAB_ADMIN_ROLE]
