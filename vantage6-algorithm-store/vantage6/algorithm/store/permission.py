import logging

from vantage6.common import logger_name

from vantage6.backend.common.permission import PermissionManagerBase, RuleCollectionBase
from vantage6.backend.common.resource.error_handling import (
    UnauthorizedError,
)

from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Operation, Rule

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class RuleCollection(RuleCollectionBase):
    """
    Class that tracks a set of all rules for a certain resource name for
    permissions of the algorithm store
    """

    def has_permission(self, operation: str) -> bool:
        """
        Check if the user has the permission fo a certain operation

        Parameters
        ----------
        operation: str
            Operation to check

        Returns
        -------
        bool
            True if the entity has at least the scope, False otherwise
        """
        perm = getattr(self, operation, None)

        if perm and perm.can():
            return True

        return False


class PermissionManager(PermissionManagerBase):
    def assign_rule_to_fixed_role(
        self, fixedrole: str, resource: str, operation: Operation
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
            role = Role(
                name=fixedrole, description=f"{fixedrole} role", is_default_role=True
            )
            role.save()

        rule = Rule.get_by_(name=resource, operation=operation)
        rule_params = f"{resource},{operation}"

        if not rule:
            log.error(f"Rule ({rule_params}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            role.save()
            log.info(f"Rule ({rule_params}) added to {fixedrole} role!")

    def register_rule(
        self, resource: str, operation: Operation, description=None
    ) -> None:
        """
        Register a permission rule in the database without the scope.

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

        """
        # verify that the rule is in the DB, so that these can be assigned to
        # roles and users
        rule = Rule.get_by_(name=resource, operation=operation)
        if not rule:
            rule = Rule(
                name=resource, operation=operation.value, description=description
            )
            rule.save()
            log.debug(
                "New auth rule '%s' with operation=%s is stored in the DB",
                resource,
                operation,
            )

        # assign all new rules to root user
        self.assign_rule_to_root(resource, operation)

        self.collection(resource).add(operation=rule.operation, shorten=False)

    def check_user_rules(self, rules: list[Rule]):
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.algorithm.store.model.rule.Rule`]
            List of rules that user is checked to have

        Raises
        -------
        UnauthorizedError
        """
        for rule in rules:
            if not self.collections[rule.name].has_permission(rule.operation):
                raise UnauthorizedError(
                    f"You don't have the rule ({rule.name}, {rule.operation})"
                )

    def get_new_collection(self, name: str) -> RuleCollection:
        """
        Initialize and return a new StoreRuleCollection.

        Parameters
        ----------
        name: str
            Name of the collection

        Returns
        -------
        RuleCollectionBase
            New StoreRuleCollection
        """
        return RuleCollection(name)
