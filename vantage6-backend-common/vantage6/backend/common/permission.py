from __future__ import annotations

import logging
import importlib
from abc import ABC, abstractmethod

from collections import namedtuple
from flask_principal import Permission

from vantage6.server.globals import RESOURCES
from vantage6.server.default_roles import DefaultRole
from vantage6.backend.common.base import Base
from vantage6.server.utils import obtain_auth_collaborations, obtain_auth_organization
from vantage6.common import logger_name

from vantage6.backend.common.permission_interfaces import (RoleInterface, RuleInterface,
                                                           OperationInterface, ScopeInterface)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])


class RuleCollection(ABC, dict):
    """
    Class that tracks a set of all rules for a certain resource name

    Parameters
    ----------
    name: str
        Name of the resource endpoint (e.g. node, organization, user)
    """

    def __new__(
            cls, name: str, scope: ScopeInterface = None
    ) -> ScopedRuleCollection | UnscopedRuleCollection:
        if scope:
            return ScopedRuleCollection(name, scope)
        else:
            return UnscopedRuleCollection(name)

    @abstractmethod
    def add(self, *args, **kwargs) -> None:
        """
        Add a rule to the rule collection
        """
        pass


class UnscopedRuleCollection(RuleCollection):
    """
    Class that tracks a set of all rules for a certain resource name for
    permissions that does not include a scope.

    Parameters
    ----------
    name: str
        Name of the resource endpoint (e.g. node, organization, user)
    """
    def __init__(self, name):
        self.name = name

    def add(self, operation: str) -> None:
        """
        Add a rule to the rule collection

        Parameters
        ----------
        operation: Operation
            What operation the rule applies to
        """
        permission = Permission(RuleNeed(self.name, None, operation))

        self.__setattr__(f"{operation}", permission)

    def has_permission(self, operation: OperationInterface) -> bool:
        """
        Check if the user has the permission fo a certain operation

        Parameters
        ----------
        operation: OperationInterface
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


class ScopedRuleCollection(RuleCollection):
    """
    Class that tracks a set of all rules for a certain resource name for
    permissions that include a scope.

    Parameters
    ----------
    name: str
        Name of the resource endpoint (e.g. node, organization, user)
    """

    def __init__(self, name: str, scope: ScopeInterface) -> None:
        self.name = name
        self.scope = scope

    def add(self, scope: ScopeInterface, operation: OperationInterface) -> None:
        """
        Add a rule to the rule collection

        Parameters
        ----------
        scope: ScopeInterface
            Scope within which to apply the rule
        operation: Operation
            What operation the rule applies to
        """
        permission = Permission(RuleNeed(self.name, scope, operation))
        self.__setattr__(f"{operation}_{scope}", permission)

    def can_for_org(self, operation: OperationInterface, subject_org_id: int | str) -> bool:
        """
        Check if an operation is allowed on a certain organization

        Parameters
        ----------
        operation: OperationInterface
            Operation to check if allowed
        subject_org_id: int | str
            Organization id on which the operation should be allowed. If a
            string is given, it will be converted to an int

        Returns
        -------
        bool
            True if the operation is allowed on the organization, False
            otherwise
        """
        if isinstance(subject_org_id, str):
            subject_org_id = int(subject_org_id)

        auth_org = obtain_auth_organization()

        # check if the entity has global permission
        global_perm = getattr(self, f"{operation}_{self.scope.GLOBAL}")
        if global_perm and global_perm.can():
            return True

        # check if the entity has organization permission and organization is
        # the same as the subject organization
        org_perm = getattr(self, f"{operation}_{self.scope.ORGANIZATION}")
        if auth_org.id == subject_org_id and org_perm and org_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # organization is in the collaboration of the own organization
        col_perm = getattr(self, f"{operation}_{self.scope.COLLABORATION}")
        if col_perm and col_perm.can():
            for col in auth_org.collaborations:
                if subject_org_id in [org.id for org in col.organizations]:
                    return True

        # no permission found
        return False

    def can_for_col(self, operation: OperationInterface, collaboration_id: int | str) -> bool:
        """
        Check if the user or node can perform the operation on a certain
        collaboration

        Parameters
        ----------
        operation: Operation
            Operation to check if allowed
        collaboration_id: int | str
            Collaboration id on which the operation should be allowed. If a
            string is given, it will be converted to an int
        """
        if isinstance(collaboration_id, str):
            collaboration_id = int(collaboration_id)

        auth_collabs = obtain_auth_collaborations()

        # check if the entity has global permission
        global_perm = getattr(self, f"{operation}_{self.scope.GLOBAL}")
        if global_perm and global_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # collaboration is in the collaborations of the user/node
        col_perm = getattr(self, f"{operation}_{self.scope.COLLABORATION}")
        if (
                col_perm
                and col_perm.can()
                and self._id_in_list(collaboration_id, auth_collabs)
        ):
            return True

        # no permission found
        return False

    def get_max_scope(self, operation: OperationInterface) -> ScopeInterface | None:
        """
        Get the highest scope that the entity has for a certain operation

        Parameters
        ----------
        operation: Operation
            Operation to check

        Returns
        -------
        Scope | None
            Highest scope that the entity has for the operation. None if the
            entity has no permission for the operation
        """
        if getattr(self, f"{operation}_{self.scope.GLOBAL}"):
            return self.scope.GLOBAL
        elif getattr(self, f"{operation}_{self.scope.COLLABORATION}"):
            return self.scope.COLLABORATION
        elif getattr(self, f"{operation}_{self.scope.ORGANIZATION}"):
            return self.scope.ORGANIZATION
        elif getattr(self, f"{operation}_{self.scope.OWN}"):
            return self.scope.OWN
        else:
            return None

    def has_at_least_scope(self, scope: ScopeInterface, operation: OperationInterface) -> bool:
        """
        Check if the entity has at least a certain scope for a certain
        operation

        Parameters
        ----------
        scope: Scope
            Scope to check if the entity has at least
        operation: Operation
            Operation to check

        Returns
        -------
        bool
            True if the entity has at least the scope, False otherwise
        """
        scopes: list[ScopeInterface] = self._get_scopes_from(scope)
        for s in scopes:
            perm = getattr(self, f"{operation}_{s}", None)
            if perm and perm.can():
                return True
        return False

    def _id_in_list(self, id_: int, resource_list: list[Base]) -> bool:
        """
        Check if resource list contains a resource with a certain ID

        Parameters
        ----------
        id_ : int
            ID of the resource
        resource_list : list[db.Base]
            List of resources

        Returns
        -------
        bool
            True if resource is in list, False otherwise
        """
        return any(r.id == id_ for r in resource_list)

    def _get_scopes_from(self, minimal_scope: ScopeInterface) -> list[ScopeInterface]:
        """
        Get scopes that are at least equal to a certain scope

        Parameters
        ----------
        minimal_scope: Scope
            Minimal scope

        Returns
        -------
        list[Scope]
            List of scopes that are at least equal to the minimal scope

        Raises
        ------
        ValueError
            If the minimal scope is not known
        """
        if minimal_scope == self.scope.ORGANIZATION:
            return [self.scope.ORGANIZATION, self.scope.COLLABORATION, self.scope.GLOBAL]
        elif minimal_scope == self.scope.COLLABORATION:
            return [self.scope.COLLABORATION, self.scope.GLOBAL]
        elif minimal_scope == self.scope.GLOBAL:
            return [self.scope.GLOBAL]
        elif minimal_scope == self.scope.OWN:
            return [self.scope.OWN, self.scope.ORGANIZATION, self.scope.COLLABORATION, self.scope.GLOBAL]
        else:
            raise ValueError(f"Unknown scope '{minimal_scope}'")


class PermissionManager(ABC):
    """
    Loads the permissions and syncs rules in database with rules defined in
    the code
    """

    def __init__(self,
                 resources_location: str,
                 role: RoleInterface,
                 rule: RuleInterface,
                 operation: OperationInterface,
                 ) -> None:

        self.role = role
        self.rule = rule
        self.operation = operation
        log.info("Loading permission system...")
        self.load_rules_from_resources(resources_location)

    @abstractmethod
    def assign_rule_to_fixed_role(
            self, *args, **kwargs
    ) -> None:
        """
        Attach a rule to a fixed role (not adjustable by users).

        Parameters
        ----------
        fixedrole: str
            Name of the fixed role that the rule should be added to
        resource: str
            Resource that the rule applies to
        scope: Scope
            Scope that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        pass

    @abstractmethod
    def register_rule(
            self,
            *args, **kwargs
    ) -> None:
        """
            Register a permission rule in the database.
        """
        pass

    @abstractmethod
    def check_user_rules(self, rules: list[RuleInterface]) -> dict | None:
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.server.model.rule.Rule`]
            List of rules that user is checked to have

        Returns
        -------
        dict | None
            Dict with a message which rule is missing, else None
        """
        pass

    def load_rules_from_resources(self, resources_location: str) -> None:
        """
        Collect all permission rules from all registered API resources
        """
        for res in RESOURCES:
            module = importlib.import_module(f"{resources_location}.{res}")
            try:
                module.permissions(self)
            except Exception:
                module_name = module.__name__.split(".")[-1]
                log.debug(
                    "Resource '%s' contains no or invalid permissions", module_name
                )

    def assign_rule_to_root(
            self, *args, **kwargs
    ) -> None:
        """
        Assign a rule to the root role.

        resource: str
            Resource that the rule applies to
        operation: OperationInterface
            Operation that the rule applies to
        scope: ScopeInterface
            Scope that the rule applies to
        """

        self.assign_rule_to_fixed_role(DefaultRole.ROOT, *args, **kwargs)

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
            self.collections[name] = RuleCollection(name, self.scope) if hasattr(self, "scope") \
                else RuleCollection(name)
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


class ScopedPermissionManager(PermissionManager):

    def __init__(self, resources_location: str, role: RoleInterface, rule: RuleInterface,
                 operation: OperationInterface, scope: ScopeInterface):
        super().__init__(resources_location, role, rule, operation)
        self.scope = scope
        self.collections: dict[str, ScopedRuleCollection] = {}

    def assign_rule_to_node(
            self, resource: str, scope: ScopeInterface, operation: OperationInterface
    ) -> None:
        """
        Assign a rule to the Node role.

        Parameters
        ----------
        resource: str
            Resource that the rule applies to
        scope: ScopeInterface
            Scope that the rule applies to
        operation: OperationInterface
            Operation that the rule applies to
        """
        self.assign_rule_to_fixed_role(DefaultRole.NODE, resource, operation, scope)

    def assign_rule_to_container(
            self, resource: str, scope: ScopeInterface, operation: OperationInterface
    ) -> None:
        """
        Assign a rule to the container role.

        Parameters
        ----------
        resource: str
            Resource that the rule applies to
        scope: Scope
            Scope that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        self.assign_rule_to_fixed_role(
            DefaultRole.CONTAINER, resource, operation, scope
        )

    def assign_rule_to_fixed_role(
            self, fixedrole: str, resource: str, operation: OperationInterface,
            scope: ScopeInterface
    ) -> None:
        """
        Attach a rule to a fixed role (not adjustable by users).

        Parameters
        ----------
        fixedrole: str
            Name of the fixed role that the rule should be added to
        resource: str
            Resource that the rule applies to
        scope: Scope
            Scope that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        role = self.role.get_by_name(fixedrole)
        if not role:
            log.warning(f"{fixedrole} role not found, creating it now!")
            role = self.role(
                    name=fixedrole, description=f"{fixedrole} role", is_default_role=True
                )

        rule = self.rule.get_by_(resource, scope, operation)
        rule_params = f"{resource},{scope},{operation}"

        if not rule:
            log.error(f"Rule ({rule_params}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(
                f"Rule ({rule_params}) added to " f"{fixedrole} role!"
            )

    def register_rule(
            self,
            resource: str,
            operation: OperationInterface,
            scope: ScopeInterface,
            description=None,
            assign_to_node=False,
            assign_to_container=False,
    ) -> None:
        """
            Register a permission rule in the database with the scope.

            If a rule already exists, nothing is done. This rule can be used in API
            endpoints to determine if a user, node or container can do a certain
            operation in a certain scope.

            Parameters
            ----------
            resource : str
                API resource that the rule applies to
            operation : OperationInterface
                Operation of the rule
            scope : ScopeInterface
                Scope of the rule
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
        rule = self.rule.get_by_(resource, scope, operation)
        if not rule:
            rule = self.rule(
                name=resource, operation=operation, scope=scope, description=description
            )
            rule.save()
            log.debug(
                "New auth rule '%s' with scope=%s and operation=%s is stored in the DB",
                resource,
                scope,
                operation,
            )

        if assign_to_container:
            self.assign_rule_to_container(resource, scope, operation)

        if assign_to_node:
            self.assign_rule_to_node(resource, scope, operation)

        # assign all new rules to root user
        self.assign_rule_to_root(resource, operation, scope)

        self.collection(resource).add(rule.scope, rule.operation)

    def check_user_rules(self, rules: list[RuleInterface]) -> dict | None:
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.server.model.rule.Rule`]
            List of rules that user is checked to have

        Returns
        -------
        dict | None
            Dict with a message which rule is missing, else None
        """
        for rule in rules:
            if not self.collections[rule.name].has_at_least_scope(
                    rule.scope, rule.operation
            ):
                return {
                    "msg": f"You don't have the rule ({rule.name}, "
                           f"{rule.scope.name.lower()}, "
                           f"{rule.operation.name.lower()})"
                }
        return None


class UnscopedPermissionManager(PermissionManager):

    def __init__(self, resources_location: str, role: RoleInterface, rule: RuleInterface,
                 operation: OperationInterface):
        super().__init__(resources_location, role, rule, operation)
        self.collections: dict[str, UnscopedRuleCollection] = {}

    def assign_rule_to_fixed_role(
            self, fixedrole: str, resource: str, operation: OperationInterface

    ) -> None:
        """
        Attach a rule to a fixed role (not adjustable by users).

        Parameters
        ----------
        fixedrole: str
            Name of the fixed role that the rule should be added to
        resource: str
            Resource that the rule applies to
        operation: OperationInterface
            Operation that the rule applies to
        """
        role = self.role.get_by_name(fixedrole)
        if not role:
            log.warning(f"{fixedrole} role not found, creating it now!")
            role = self.role(name=fixedrole, description=f"{fixedrole} role")

        rule = self.rule.get_by_(resource, operation)
        rule_params = f"{resource},{operation}"

        if not rule:
            log.error(f"Rule ({rule_params}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(
                f"Rule ({rule_params}) added to " f"{fixedrole} role!"
            )

    def register_rule(
            self, resource: str, operation: OperationInterface, description=None
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
            operation : OperationInterface
                Operation of the rule
            description : String, optional
                Human readable description where the rule is used for, by default
                None

        """
        # verify that the rule is in the DB, so that these can be assigned to
        # roles and users
        rule = self.rule.get_by_(resource, operation)
        if not rule:
            rule = self.rule(name=resource, operation=operation, description=description)
            rule.save()
            log.debug(
                f"New auth rule '{resource}' with"
                f" operation={operation} is stored in the DB"
            )

        # assign all new rules to root user
        self.assign_rule_to_root(resource, operation)

        self.collection(resource).add(rule.operation)

    @abstractmethod
    def check_user_rules(self, rules: list[RuleInterface]) -> dict | None:
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.server.model.rule.Rule`]
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
