# TODO this file is awkward...
import logging

# Note: by importing these classes, the classes are registered in the Base's
# SQLAlchemy metadata. This is required for SQLAlchemy to be able to map the
# classes to the database tables, and e.g. initialize the database tables on
# startup.
from vantage6.algorithm.store.model import (
    Base,
    Algorithm,
    Argument,
    Database,
    Function,
    Permission,
    Role,
    Rule,
    User,
    Review,
    Vantage6Server,
    role_rule_association,
    Policy,
)
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


