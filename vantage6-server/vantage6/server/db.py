import logging

# TODO this file is awkward...
from vantage6.server.model import (
    Base,
    AlgorithmPort,
    AlgorithmStore,
    Authenticatable,
    Collaboration,
    Member,
    Node,
    NodeConfig,
    Organization,
    Permission,
    Role,
    role_rule_association,
    Rule,
    Run,
    Study,
    StudyMember,
    Task,
    TaskDatabase,
    User,
    UserPermission,
)
from vantage6.common import logger_name


module_name = logger_name(__name__)
log = logging.getLogger(module_name)

