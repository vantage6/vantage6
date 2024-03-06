import logging
import importlib

from collections import namedtuple
from flask_principal import Permission

from vantage6.algorithm.store.globals import RESOURCES
from vantage6.algorithm.store.default_roles import DefaultRole
from vantage6.algorithm.store.model.base import Base
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule, Operation
from vantage6.algorithm.store.model.base import DatabaseSessionManager
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = namedtuple("RuleNeed", ["name", "operation"])


class RuleCollection(dict):
    """
    Class that tracks a set of all rules for a certain resource name

    Parameters
    ----------
    name: str
        Name of the resource endpoint (e.g. node, organization, user)
    """

    def __init__(self, name: str) -> None:
        self.name = name

    def add(self, operation: Operation) -> None:
        """
        Add a rule to the rule collection

        Parameters
        ----------
        operation: Operation
            What operation the rule applies to
        """
        permission = Permission(RuleNeed(self.name, operation))
        self.__setattr__(f"{operation}", permission)

    def has_permission(self, operation: Operation) -> bool:
        """
        Check if the user has the permission fo a certain operation

        Parameters
        ----------
        operation: Operation
            Operation to check

        Returns
        -------
        bool
            True if the entity has at least the scope, False otherwise
        """
        perm = getattr(self, f"{operation}", None)

        if perm and perm.can():
            return True

        return False


class PermissionManager:
    """
    Loads the permissions and syncs rules in database with rules defined in
    the code
    """

    def __init__(self) -> None:
        self.collections: dict[str, RuleCollection] = {}
        log.info("Loading permission system...")
        self.load_rules_from_resources()

    def load_rules_from_resources(self) -> None:
        """
        Collect all permission rules from all registered API resources
        """
        for res in RESOURCES:
            module = importlib.import_module("vantage6.algorithm.store.resource." + res)
            try:
                module.permissions(self)
            except Exception as e:
                module_name = module.__name__.split(".")[-1]
                log.debug(
                    f"Resource '{module_name}' contains no or invalid permissions."
                )

    def assign_rule_to_root(self, name: str, operation: Operation) -> None:
        """
        Assign a rule to the root role.

        resource: str
            Resource that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        self.assign_rule_to_fixed_role(DefaultRole.ROOT, name, operation)

    @staticmethod
    def assign_rule_to_fixed_role(
        fixedrole: str, resource: str, operation: Operation
    ) -> None:
        """
        Attach a rule to a fixed role (not adjustable by users).

        Parameters
        ----------
        fixedrole: str
            Name of the fixed role that the rule should be added to
        resource: str
            Resource that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        role = Role.get_by_name(fixedrole)
        if not role:
            log.warning(f"{fixedrole} role not found, creating it now!")
            role = Role(name=fixedrole, description=f"{fixedrole} role")

        rule = Rule.get_by_(resource, operation)
        if not rule:
            log.error(f"Rule ({resource},{operation}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(f"Rule ({resource},{operation}) added to " f"{fixedrole} role!")

    def register_rule(
        self, resource: str, operation: Operation, description=None
    ) -> None:
        """
        Register a permission rule in the database.

        If a rule already exists, nothing is done. This rule can be used in API
        endpoints to determine if a user, node or container can do a certain
        operation in a certain scope.

        Parameters
        ----------
        resource : str
            API resource that the rule applies to
        operation : Operation
            Operation of the rule
        description : String, optional
            Human readable description where the rule is used for, by default
            None
        assign_to_node: bool, optional
            Whether rule should be assigned to the node role or not. Default
            False
        assign_to_container: bool, optional
            Whether rule should be assigned to the container role or not.
            Default False
        """
        # verify that the rule is in the DB, so that these can be assigned to
        # roles and users
        rule = Rule.get_by_(resource, operation)
        if not rule:
            rule = Rule(name=resource, operation=operation, description=description)
            rule.save()
            log.debug(
                f"New auth rule '{resource}' with"
                f" operation={operation} is stored in the DB"
            )

        # assign all new rules to root user
        self.assign_rule_to_root(resource, operation)

        self.collection(resource).add(rule.operation)

    def appender(self, name: str) -> callable:
        """
        Add a module's rules to the rule collection

        Parameters
        ----------
        name: str
            The name of the module whose rules are to be registered

        Returns
        -------
        Callable
            A callable ``register_rule`` function
        """
        # make sure collection exists
        self.collection(name)
        return lambda *args, **kwargs: self.register_rule(name, *args, **kwargs)

    def collection(self, name: str) -> RuleCollection:
        """
        Get a RuleCollection object. If it doesn't exist yet, it will be
        created.

        Parameters
        ----------
        name: str
            Name of the module whose RuleCollection is to be obtained or
            created

        Returns
        -------
        RuleCollection
            The collection of rules belonging to the module name
        """
        if self._collection_exists(name):
            return self.collections[name]
        else:
            self.collections[name] = RuleCollection(name)
            return self.collections[name]

    def _collection_exists(self, name: str) -> bool:
        """
        Check if a module's rule collection is defined

        Parameters
        ----------
        name: str
            Name of the module to be checked

        Returns
        -------
        bool:
            True if RuleCollection is defined for module, else False
        """
        return name in self.collections

    def __getattr__(self, name: str) -> RuleCollection:
        # TODO BvB 2023-01-18 I think this function might not be used. It would
        # be triggered when we do something like
        # `permissionManager.resource_name` but we don't ever do that (?!)
        try:
            collection = self.collections[name]
            return collection
        except Exception as e:
            log.critical(f"Missing permission collection! {name}")
            raise e

    @staticmethod
    def rule_exists_in_db(name: str, operation: Operation) -> bool:
        """Check if the rule exists in the DB.

        Parameters
        ----------
        name: str
            Name of the rule
        operation: Operation
            Operation of the rule

        Returns
        -------
        bool
            Whenever this rule exists in the database or not
        """
        session = DatabaseSessionManager.get_session()
        result = (
            session.query(Rule)
            .filter_by(
                name=name,
                operation=operation,
            )
            .scalar()
        )
        session.commit()
        return result

    def check_user_rules(self, rules: list[Rule]) -> dict | None:
        """
        Check if a user has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.algorithm.store.model.rule.Rule`]
            List of rules that user is checked to have

        Returns
        -------
        dict | None
            Dict with a message which rule is missing, else None
        """
        for rule in rules:
            if not self.collections[rule.name].has_permission(rule.operation):
                return {
                    "msg": f"You don't have the rule ({rule.name}, "
                    f"{rule.operation})"
                }
        return None
