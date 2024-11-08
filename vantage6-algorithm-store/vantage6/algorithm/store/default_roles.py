from enum import Enum

from vantage6.algorithm.store.model.rule import Operation, Rule


class DefaultRole(str, Enum):
    """Enum containing the names of the default roles"""

    DEVELOPER = "Developer"
    ROOT = "Root"
    REVIEWER = "Reviewer"
    STORE_MANAGER = "Store Manager"
    ALGORITHM_MANAGER = "Algorithm Manager"
    VIEWER = "Viewer"
    SERVER_MANAGER = "Server Manager"


def get_default_roles() -> list[dict]:
    """
    Get a list containing the default roles and their rules, so that they may
    be created in the database

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
        "rules": Rule.get(),
    }
    # 2. Role for viewing algorithms
    VIEWER_RULES = [
        Rule.get_by_("algorithm", Operation.VIEW),
        Rule.get_by_("user", Operation.VIEW),
        Rule.get_by_("role", Operation.VIEW),
        Rule.get_by_("review", Operation.VIEW),
    ]
    VIEWER_ROLE = {
        "name": DefaultRole.VIEWER,
        "description": "Can view algorithm store resources",
        "rules": VIEWER_RULES,
    }
    # 3. Reviewer role
    REVIEWER_RULES = VIEWER_RULES + [Rule.get_by_("review", Operation.EDIT)]
    REVIEWER_ROLE = {
        "name": DefaultRole.REVIEWER,
        "description": "Can view resources and review algorithms",
        "rules": REVIEWER_RULES,
    }
    # 4. Store manager role
    STORE_MANAGER = VIEWER_RULES + [
        Rule.get_by_("user", Operation.CREATE),
        Rule.get_by_("user", Operation.EDIT),
        Rule.get_by_("user", Operation.DELETE),
        Rule.get_by_("role", Operation.CREATE),
        Rule.get_by_("role", Operation.EDIT),
        Rule.get_by_("role", Operation.DELETE),
    ]
    STORE_MANAGER = {
        "name": DefaultRole.STORE_MANAGER,
        "description": "Can view resources and manage users and roles.",
        "rules": STORE_MANAGER,
    }
    # Algorithm manager role
    ALGORITHM_MANAGER_RULES = REVIEWER_RULES + [
        Rule.get_by_("algorithm", Operation.CREATE),
        Rule.get_by_("algorithm", Operation.EDIT),
        Rule.get_by_("algorithm", Operation.DELETE),
        Rule.get_by_("review", Operation.CREATE),
        Rule.get_by_("review", Operation.DELETE),
    ]
    ALGORITHM_MANAGER = {
        "name": DefaultRole.ALGORITHM_MANAGER,
        "description": "Can view store resources and manage algorithms and reviews.",
        "rules": ALGORITHM_MANAGER_RULES,
    }
    # Developer role
    DEVELOPER_RULES = VIEWER_RULES + [
        Rule.get_by_("algorithm", Operation.CREATE),
        Rule.get_by_("algorithm", Operation.EDIT),
    ]
    DEVELOPER_ROLE = {
        "name": DefaultRole.DEVELOPER,
        "description": "Can view store resources and create new algorithms.",
        "rules": DEVELOPER_RULES,
    }
    # server manager role
    SERVER_MANAGER_RULES = [
        Rule.get_by_("vantage6_server", Operation.DELETE),
    ]
    SERVER_MANAGER_ROLE = {
        "name": "Server Manager",
        "description": (
            "Can delete their own whitelisted vantage6 server. This rule is"
            " assigned automatically upon whitelisting a server"
        ),
        "rules": SERVER_MANAGER_RULES,
    }
    # Combine all in array
    return [
        SUPER_ROLE,
        VIEWER_ROLE,
        REVIEWER_ROLE,
        STORE_MANAGER,
        ALGORITHM_MANAGER,
        DEVELOPER_ROLE,
        SERVER_MANAGER_ROLE,
    ]
