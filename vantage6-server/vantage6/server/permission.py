import logging

from collections import namedtuple
from flask_principal import Permission, PermissionDenied

from vantage6.server.model.role import Role
from vantage6.server.model.rule import Rule, Operation, Scope
from vantage6.server.model.base import Database
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


# create a Need which is used by prinicipal
RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])


_node_rules = []
_container_rules = []


def assign_rule_to_node(name: str, scope: Scope, operation: Operation):
    assign_rule_to_fixed_role("node", name, scope, operation)


def assign_rule_to_container(name: str, scope: Scope, operation: Operation):
    assign_rule_to_fixed_role("container", name, scope, operation)


def assign_rule_to_fixed_role(fixedrole: str, name: str, scope: Scope,
                              operation: Operation):
    """Make sure that all the rules are attached to the node role."""
    role = Role.get_by_name(fixedrole)
    if not role:
        log.warning("Node role not found, creating it now!")
        role = Role(name=fixedrole, description="Node role used by all nodes")

    rule = Rule.get_by_(name, scope, operation)
    if not rule:
        log.error(f"Rule ({name},{scope},{operation}) not found!")

    if rule not in role.rules:
        role.rules.append(rule)
        log.info(f"Rule ({name},{scope},{operation}) added to node role!")


def valid_rule_need(name: str, scope: Scope, operation: Operation):
    """Check that rule exists in DB and return it if this is the case.

    Parameters
    ----------
    name : str
        (Unique) name to identify the rule
    scope : Scope
        Enum to determine the scope
    operation : Operation
        Enum to determine the operation

    Returns
    -------
    RuleNeed
        A named tuple containing a permission 'Need'

    Raises
    ------
    Exception
        In case a rule is requested that does not exist an error is raised.
    """
    if not rule_exists(name, scope, operation):
        raise Exception("Assigning rule that does not exist!")

    return RuleNeed(name, scope, operation)


def register_rule(rule: str, scope: Scope, operation: Operation,
                  description=None, assign_to_node=False,
                  assign_to_container=False):
    """Register a rule in the database.

    If a rule already exists, nothing is done. This rule can be used in API
    endpoints to determine if a user can do a certain operation in a certain
    scope.

    Parameters
    ----------
    rule : str
        (Unique) name of the rule
    scope : Scope
        List of available scopes of this rule
    operation : Operation
        List of available operations on this rule
    description : String, optional
        Human readable description where the rule is used for, by default None

    Returns
    -------
    Permission (tuple)
        permision object that can be used in API endpoints
    """
    if not rule_exists(rule, scope, operation):
        new_rule = Rule(
            name=rule,
            operation=operation,
            scope=scope,
            description=description
        )
        new_rule.save()
        log.debug(f"New auth rule '{rule}' with scope={scope}"
                  f" and operation={operation} is added")

    if assign_to_container:
        assign_rule_to_container(rule, scope, operation)

    if assign_to_node:
        assign_rule_to_node(rule, scope, operation)

    permission = Permission(valid_rule_need(rule, scope, operation))
    return permission


def rule_exists(name, scope, operation):
    """Check if the rule exists in the DB.

    Parameters
    ----------
    name : String
        (Unique) name of the rule
    scope : Scope (Enum)
        Scope the rule
    operation : Operation (Enum)
        Operation on the entity

    Returns
    -------
    Boolean
        Whenever this rule exists in the database or not
    """
    return Database().Session.query(Rule).filter_by(
        name=name,
        operation=operation,
        scope=scope
    ).scalar()


def verify_user_rules(rules) -> dict:
    for rule in rules:
        requires = RuleNeed(rule.name, rule.scope, rule.operation)
        try:
            Permission(requires).test()
        except PermissionDenied:
            return {"msg": f"You dont have the rule ({rule.name},"
                    f"{rule.scope}, {rule.operation})"}
    return False
