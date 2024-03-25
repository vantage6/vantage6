from enum import Enum

from vantage6.algorithm.store.model.rule import Operation, Rule


class DefaultRole(str, Enum):
    """Enum containing the names of the default roles"""

    DEVELOPER = "Developer"
    ROOT = "Root"
    REVIEWER = "Reviewer"
    STORE_MANAGER = "Store Manager"
    VIEWER = "Viewer"


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
    ]
    VIEWER_ROLE = {
        "name": DefaultRole.VIEWER,
        "description": "Can view accounts and algorithms",
        "rules": VIEWER_RULES,
    }
    # 3. Reviewer role
    REVIEWER_RULES = [
        Rule.get_by_("algorithm", Operation.VIEW),
        Rule.get_by_("algorithm", Operation.REVIEW),
    ]
    REVIEWER_ROLE = {
        "name": DefaultRole.REVIEWER,
        "description": "Can view, edit and delete algorithms",
        "rules": REVIEWER_RULES,
    }
    # 4. Store manager role
    STORE_MANAGER = [
        Rule.get_by_("algorithm", Operation.VIEW),
        Rule.get_by_("algorithm", Operation.CREATE),
        Rule.get_by_("algorithm", Operation.DELETE),
        Rule.get_by_("user", Operation.CREATE),
        Rule.get_by_("user", Operation.EDIT),
    ]
    STORE_MANAGER = {
        "name": DefaultRole.STORE_MANAGER,
        "description": "Can manage algorithms, and create and edit users.",
        "rules": STORE_MANAGER,
    }
    # 4. Developer role
    DEVELOPER_RULES = [
        Rule.get_by_("algorithm", Operation.VIEW),
        Rule.get_by_("algorithm", Operation.CREATE),
        Rule.get_by_("algorithm", Operation.EDIT),
    ]
    DEVELOPER_ROLE = {
        "name": DefaultRole.DEVELOPER,
        "description": "Can view and create algorithms.",
        "rules": DEVELOPER_RULES,
    }
    # Combine all in array
    return [SUPER_ROLE, VIEWER_ROLE, REVIEWER_ROLE, STORE_MANAGER, DEVELOPER_ROLE]
