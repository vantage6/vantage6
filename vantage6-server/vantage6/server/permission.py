import logging

from collections import namedtuple
from enum import Enum
from vantage6.server.db import Rule
from vantage6.server.model.base import Database

RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

class Operation:
    VIEW = 0
    EDIT = 1
    CREATE = 2
    DELETE = 3


class Scope:
    OWN = 0
    ORGANIZATION = 1
    COLLABORATION = 2
    GLOBAL = 3


def register_rule(rule: str, scopes: list, operations: list, description=None):

    for operation in operations:
        for scope in scopes:
            if Database().Session.query(Rule.id).filter_by(
                name=rule,
                operation=operation,
                scope=scope
            ).scalar() is None:
                new_rule = Rule(
                    name=rule,
                    operation=operation,
                    scope=scope,
                    description=description
                )
                new_rule.save()
            else:
                pass
                # log.debug(f"Rule '{rule}'")