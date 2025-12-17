import logging

from flask import g

from vantage6.common import logger_name

from vantage6.backend.common.permission import (
    PermissionManagerBase,
    RuleCollectionBase,
    get_attribute_name,
)
from vantage6.backend.common.resource.error_handling import UnauthorizedError

from vantage6.server import db
from vantage6.server.model.base import Base
from vantage6.server.model.role import Role
from vantage6.server.model.rule import Operation, Rule, Scope

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def obtain_auth_collaborations() -> list[db.Collaboration]:
    """
    Obtain the collaborations that the auth is part of.

    Returns
    -------
    list[db.Collaboration]
        List of collaborations
    """
    if g.user:
        return g.user.organization.collaborations
    elif g.node:
        return g.node.organization.collaborations
    else:
        return [db.Collaboration.get(g.container["collaboration_id"])]


def obtain_auth_organization() -> db.Organization:
    """
    Obtain the organization model from the auth that is logged in.

    Returns
    -------
    db.Organization
        Organization model
    """
    if g.user:
        org_id = g.user.organization.id
    elif g.node:
        org_id = g.node.organization.id
    else:
        org_id = g.container["organization_id"]
    return db.Organization.get(org_id)


class RuleCollection(RuleCollectionBase):
    """
    Class that tracks a set of all rules for a certain resource name for
    permissions of the vantage6 server.
    """

    def allowed_for_org(self, operation: Operation, subject_org_id: int | str) -> bool:
        """
        Check if an operation is allowed on a certain organization

        Parameters
        ----------
        operation: Operation
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
        global_perm = getattr(self, get_attribute_name(operation, Scope.GLOBAL))
        if global_perm and global_perm.can():
            return True

        # check if the entity has organization permission and organization is
        # the same as the subject organization
        org_perm = getattr(self, get_attribute_name(operation, Scope.ORGANIZATION))
        if auth_org.id == subject_org_id and org_perm and org_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # organization is in the collaboration of the own organization
        col_perm = getattr(self, get_attribute_name(operation, Scope.COLLABORATION))
        if col_perm and col_perm.can():
            for col in auth_org.collaborations:
                if subject_org_id in [org.id for org in col.organizations]:
                    return True

        # no permission found
        return False

    def can_for_col(self, operation: Operation, collaboration_id: int | str) -> bool:
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
        global_perm = getattr(self, get_attribute_name(operation, Scope.GLOBAL))
        if global_perm and global_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # collaboration is in the collaborations of the user/node
        col_perm = getattr(self, get_attribute_name(operation, Scope.COLLABORATION))
        if (
            col_perm
            and col_perm.can()
            and self._id_in_list(collaboration_id, auth_collabs)
        ):
            return True

        # no permission found
        return False

    def get_max_scope(self, operation: Operation) -> Scope | None:
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
        if getattr(self, get_attribute_name(operation, Scope.GLOBAL)):
            return Scope.GLOBAL
        elif getattr(self, get_attribute_name(operation, Scope.COLLABORATION)):
            return Scope.COLLABORATION
        elif getattr(self, get_attribute_name(operation, Scope.ORGANIZATION)):
            return Scope.ORGANIZATION
        elif getattr(self, get_attribute_name(operation, Scope.OWN)):
            return Scope.OWN
        else:
            return None

    def has_at_least_scope(self, scope: Scope, operation: Operation) -> bool:
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
        scopes: list[Scope] = self._get_scopes_from(scope)
        for s in scopes:
            perm = getattr(self, get_attribute_name(operation, s), None)
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

    def _get_scopes_from(self, minimal_scope: Scope) -> list[Scope]:
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
        if minimal_scope == Scope.ORGANIZATION:
            return [Scope.ORGANIZATION, Scope.COLLABORATION, Scope.GLOBAL]
        elif minimal_scope == Scope.COLLABORATION:
            return [Scope.COLLABORATION, Scope.GLOBAL]
        elif minimal_scope == Scope.GLOBAL:
            return [Scope.GLOBAL]
        elif minimal_scope == Scope.OWN:
            return [Scope.OWN, Scope.ORGANIZATION, Scope.COLLABORATION, Scope.GLOBAL]
        else:
            raise ValueError(f"Unknown scope '{minimal_scope}'")


class PermissionManager(PermissionManagerBase):
    def assign_rule_to_node(
        self, resource: str, scope: Scope, operation: Operation
    ) -> None:
        """
        Assign a rule to the Node role.

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
            self.default_roles.NODE.value, resource, operation, scope
        )

    def assign_rule_to_container(
        self, resource: str, scope: Scope, operation: Operation
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
            self.default_roles.CONTAINER.value, resource, operation, scope
        )

    def assign_rule_to_fixed_role(
        self, fixedrole: str, resource: str, operation: Operation, scope: Scope
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
        role = Role.get_by_name(fixedrole)
        if not role:
            log.warning(f"{fixedrole} role not found, creating it now!")
            role = Role(
                name=fixedrole, description=f"{fixedrole} role", is_default_role=True
            )
            role.save()

        rule = Rule.get_by_(name=resource, scope=scope, operation=operation)
        rule_params = f"{resource},{scope},{operation}"

        if not rule:
            log.error(f"Rule ({rule_params}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            role.save()
            log.info(f"Rule ({rule_params}) added to {fixedrole} role!")

    def get_new_collection(self, name: str) -> RuleCollection:
        """
        Initialize and return a new ServerRuleCollection.
        Parameters
        ----------
        name: str
            Name of the collection

        Returns
        -------
        RuleCollectionBase
            New ServerRuleCollection
        """
        return RuleCollection(name)

    def register_rule(
        self,
        resource: str,
        scope: Scope,
        operation: Operation,
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
        operation : Operation
            Operation of the rule
        scope : Scope
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

        rule = Rule.get_by_(name=resource, scope=scope, operation=operation)
        if not rule:
            rule = Rule(
                name=resource,
                operation=operation.value,
                scope=scope.value,
                description=description,
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

        self.collection(resource).add(rule.operation, rule.scope)

    def check_user_rules(self, rules: list[Rule]) -> None:
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: list[:class:`~vantage6.server.model.rule.Rule`]
            List of rules that user is checked to have

        Raises
        ---------
        UnauthorizedError
        """
        for rule in rules:
            if not self.collections[rule.name].has_at_least_scope(
                rule.scope, rule.operation
            ):
                raise UnauthorizedError(
                    f"You don't have the rule ({rule.name}, {rule.scope}, "
                    f"{rule.operation})"
                )
