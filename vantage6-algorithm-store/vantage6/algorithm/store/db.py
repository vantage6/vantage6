# TODO this file is awkward...
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
    Policy,
    UserPermission,
    role_rule_association,
)
