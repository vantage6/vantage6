# TODO this file is awkward...
# Note: by importing these classes, the classes are registered in the Base's
# SQLAlchemy metadata. This is required for SQLAlchemy to be able to map the
# classes to the database tables, and e.g. initialize the database tables on
# startup.
# ruff: noqa: F401
from vantage6.algorithm.store.model import (
    Algorithm,
    AllowedArgumentValue,
    Argument,
    Base,
    Database,
    Function,
    Permission,
    Policy,
    Review,
    Role,
    Rule,
    User,
    UserPermission,
    role_rule_association,
)
