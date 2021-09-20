import collections
import logging
import importlib

from collections import namedtuple
from flask_principal import Permission, PermissionDenied

from vantage6.server.globals import RESOURCES
from vantage6.server.model.role import Role
from vantage6.server.model.rule import Rule, Operation, Scope
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])


class RuleCollection:
    """Ordering things in collections helps us in the API endpoints."""

    def __init__(self, name):
        self.name = name

    def add(self, scope: Scope, operation: Operation):
        permission = Permission(RuleNeed(self.name, scope, operation))
        self.__setattr__(f'{operation.value}_{scope.value}', permission)

    def get(self, scope: Scope, operation: Operation):
        return self.__getattribute__(f'{scope}_{operation}')


class PermissionManager:

    def __init__(self):
        self.collections = {}
        log.info("Loading permission system...")
        self.load_rules_from_resources()

    def load_rules_from_resources(self):
        for res in RESOURCES:
            module = importlib.import_module('vantage6.server.resource.' + res)
            try:
                module.permissions(self)
            except Exception:
                module_name = module.__name__.split(".")[-1]
                log.debug(f"Resource '{module_name}' contains no or invalid "
                          "permissions")

    def assign_rule_to_node(self, name: str, scope: Scope,
                            operation: Operation):
        """Assign a rule to the Node role."""
        self.assign_rule_to_fixed_role("node", name, scope, operation)

    def assign_rule_to_container(self, name: str, scope: Scope,
                                 operation: Operation):
        """Assign a rule to the container role."""
        self.assign_rule_to_fixed_role("container", name, scope, operation)

    @staticmethod
    def assign_rule_to_fixed_role(fixedrole: str, name: str, scope: Scope,
                                  operation: Operation):
        """Attach a rule to a fixed role (not adjustable by users)."""
        role = Role.get_by_name(fixedrole)
        if not role:
            log.warning(f"{fixedrole} role not found, creating it now!")
            role = Role(name=fixedrole, description=f"{fixedrole} role")

        rule = Rule.get_by_(name, scope, operation)
        if not rule:
            log.error(f"Rule ({name},{scope},{operation}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(f"Rule ({name},{scope},{operation}) added to "
                     f"{fixedrole} role!")

    def register_rule(self, collection: str, scope: Scope,
                      operation: Operation, description=None,
                      assign_to_node=False, assign_to_container=False):
        """Register a rule in the database.

        If a rule already exists, nothing is done. This rule can be used in API
        endpoints to determine if a user can do a certain operation in a
        certain scope.

        Parameters
        ----------
        rule : str
            (Unique) name of the rule
        scope : Scope
            List of available scopes of this rule
        operation : Operation
            List of available operations on this rule
        description : String, optional
            Human readable description where the rule is used for, by default
                None

        Returns
        -------
        Permission (tuple)
            permision object that can be used in API endpoints
        """

        # verify that the rule is in the DB, so that these can be assigned to
        # roles and users
        rule = Rule.get_by_(collection, scope, operation)
        if not rule:
            rule = Rule(name=collection, operation=operation, scope=scope,
                        description=description)
            rule.save()
            log.debug(f"New auth rule '{collection}' with scope={scope}"
                      f" and operation={operation} is stored in the DB")

        if assign_to_container:
            self.assign_rule_to_container(collection, scope, operation)

        if assign_to_node:
            self.assign_rule_to_node(collection, scope, operation)

        self.collection(collection).add(rule.scope, rule.operation)

    def appender(self, name):
        # make sure collection exists
        self.collection(name)
        return lambda *args, **kwargs: self.register_rule(name, *args,
                                                          **kwargs)

    def collection(self, name):
        if self._collection_exists(name):
            return self.collections[name]
        else:
            self.collections[name] = RuleCollection(name)
            return self.collections[name]

    def _collection_exists(self, name):
        return name in self.collections

    def __getattr__(self, name: str):
        # __getattr__ is called when it is not found in the usual places
        try:
            collection = self.collections[name]
            return collection
        except Exception as e:
            log.critical(f"Missing permission collection! {name}")
            raise e


    @staticmethod
    def rule_exists_in_db(name, scope, operation):
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
        session = DatabaseSessionManager.get_session()
        return session.query(Rule).filter_by(
            name=name,
            operation=operation,
            scope=scope
        ).scalar()

    def verify_user_rules(self, rules):
        for rule in rules:
            requires = RuleNeed(rule.name, rule.scope, rule.operation)
            try:
                Permission(requires).test()
            except PermissionDenied:
                return {"msg": f"You dont have the rule ({rule.name},"
                        f"{rule.scope}, {rule.operation})"}
        return False
