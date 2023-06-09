import logging
import importlib

from collections import namedtuple
from flask_principal import Permission, PermissionDenied

from vantage6.server.globals import RESOURCES
from vantage6.server.default_roles import DefaultRole
from vantage6.server.model.role import Role
from vantage6.server.model.rule import Rule, Operation, Scope
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.model.organization import Organization
from vantage6.server.model.collaboration import Collaboration
from vantage6.common import logger_name

from vantage6.server.resource import id_in_list

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])


# TODO document this function in the API reference
def get_scopes_with_level(minimal_scope: Scope) -> list[Scope]:
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
        return [Scope.OWN, Scope.ORGANIZATION, Scope.COLLABORATION,
                Scope.GLOBAL]
    else:
        raise ValueError(f"Unknown scope '{minimal_scope}'")


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

    def add(self, scope: Scope, operation: Operation) -> None:
        """
        Add a rule to the rule collection

        Parameters
        ----------
        scope: Scope
            Scope within which to apply the rule
        operation: Operation
            What operation the rule applies to
        """
        permission = Permission(RuleNeed(self.name, scope, operation))
        self.__setattr__(f'{operation.value}_{scope.value}', permission)

    def can_for_org(self, operation: Operation, subject_org_id: int,
                    own_org: Organization) -> bool:
        """
        Check if an operation is allowed on a certain organization

        Parameters
        ----------
        operation: Operation
            Operation to check if allowed
        subject_org_id: int
            Organization id on which the operation should be allowed
        own_org: Organization
            Organization of the user/node/algorithm that is performing the
            operation

        Returns
        -------
        bool
            True if the operation is allowed on the organization, False
            otherwise
        """
        # check if the entity has global permission
        global_perm = getattr(self, f'{operation.value}_{Scope.GLOBAL.value}')
        if global_perm and global_perm.can():
            return True

        # check if the entity has organization permission and organization is
        # the same as the subject organization
        org_perm = getattr(self,
                           f'{operation.value}_{Scope.ORGANIZATION.value}')
        if own_org.id == subject_org_id and org_perm and org_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # organization is in the collaboration of the own organization
        col_perm = getattr(self,
                           f'{operation.value}_{Scope.COLLABORATION.value}')
        if col_perm and col_perm.can():
            for col in own_org.collaborations:
                if subject_org_id in [org.id for org in col.organizations]:
                    return True
        # no permission found
        return False

    def _get_relevant_perms(self, operation: Operation,
                            minimal_scope: Scope) -> list[Permission]:
        """
        Get permissions that are relevant for a certain operation with at least
        the given scope

        Parameters
        ----------
        operation: Operation
            Operation to check if allowed
        minimal_scope: Scope
            Scope to check if allowed

        Returns
        -------
        list[Permission]
            List of permissions that are relevant for the operation and scope
        """
        perms = []
        scopes = get_scopes_with_level(minimal_scope)
        for scope in scopes:
            perm = getattr(self, f'{operation.value}_{scope.value}')
            if perm is not None:
                perms.append(perm)
        return perms

    # TODO check if this function is still needed
    def has_minimal_scope(self, operation: Operation,
                          minimal_scope: Scope) -> bool:
        """
        Check if a node/user/algorithm has at least the given scope for a
        certain operation

        Parameters
        ----------
        operation: Operation
            Operation to check if allowed
        minimal_scope: Scope
            Minimal scope that user/node/algorithm should have

        Returns
        -------
        bool
            True if the entity is allowed to perform the operation on at least
            the scope provided, False otherwise
        """
        perms = self._get_relevant_perms(operation, minimal_scope)
        return any([perm.can() for perm in perms])

    def can_for_col(
        self, operation: Operation, collaboration_id: int,
        auth_collabs: list[Collaboration]
    ) -> bool:
        """
        Check if the user or node can perform the operation on a certain
        collaboration

        Parameters
        ----------
        operation: Operation
            Operation to check if allowed
        collaboration_id: int
            Collaboration id on which the operation should be allowed
        auth: Authenticatable
            User or node that is performing the operation
        """
        # check if the entity has global permission
        global_perm = getattr(self, f'{operation.value}_{Scope.GLOBAL.value}')
        if global_perm and global_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # collaboration is in the collaborations of the user/node
        col_perm = getattr(self,
                           f'{operation.value}_{Scope.COLLABORATION.value}')
        if col_perm and col_perm.can() and \
                id_in_list(collaboration_id, auth_collabs):
            return True

        # no permission found
        return False


class PermissionManager:
    """
    Loads the permissions and syncs rules in database with rules defined in
    the code
    """

    def __init__(self) -> None:
        self.collections = {}
        log.info("Loading permission system...")
        self.load_rules_from_resources()

    def load_rules_from_resources(self) -> None:
        """
        Collect all permission rules from all registered API resources
        """
        for res in RESOURCES:
            module = importlib.import_module('vantage6.server.resource.' + res)
            try:
                module.permissions(self)
            except Exception:
                module_name = module.__name__.split(".")[-1]
                log.debug(f"Resource '{module_name}' contains no or invalid "
                          "permissions")

    def assign_rule_to_root(self, name: str, scope: Scope,
                            operation: Operation) -> None:
        """
        Assign a rule to the root role.

        resource: str
            Resource that the rule applies to
        scope: Scope
            Scope that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        self.assign_rule_to_fixed_role(DefaultRole.ROOT, name, scope,
                                       operation)

    def assign_rule_to_node(self, resource: str, scope: Scope,
                            operation: Operation) -> None:
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
        self.assign_rule_to_fixed_role(DefaultRole.NODE, resource, scope,
                                       operation)

    def assign_rule_to_container(self, resource: str, scope: Scope,
                                 operation: Operation) -> None:
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
        self.assign_rule_to_fixed_role(DefaultRole.CONTAINER, resource, scope,
                                       operation)

    @staticmethod
    def assign_rule_to_fixed_role(fixedrole: str, resource: str, scope: Scope,
                                  operation: Operation) -> None:
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
            role = Role(name=fixedrole, description=f"{fixedrole} role")

        rule = Rule.get_by_(resource, scope, operation)
        if not rule:
            log.error(f"Rule ({resource},{scope},{operation}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(f"Rule ({resource},{scope},{operation}) added to "
                     f"{fixedrole} role!")

    def register_rule(self, resource: str, scope: Scope,
                      operation: Operation, description=None,
                      assign_to_node=False, assign_to_container=False) -> None:
        """
        Register a permission rule in the database.

        If a rule already exists, nothing is done. This rule can be used in API
        endpoints to determine if a user, node or container can do a certain
        operation in a certain scope.

        Parameters
        ----------
        resource : str
            API resource that the rule applies to
        scope : Scope
            Scope of the rule
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
        rule = Rule.get_by_(resource, scope, operation)
        if not rule:
            rule = Rule(name=resource, operation=operation, scope=scope,
                        description=description)
            rule.save()
            log.debug(f"New auth rule '{resource}' with scope={scope}"
                      f" and operation={operation} is stored in the DB")

        if assign_to_container:
            self.assign_rule_to_container(resource, scope, operation)

        if assign_to_node:
            self.assign_rule_to_node(resource, scope, operation)

        # assign all new rules to root user
        self.assign_rule_to_root(resource, scope, operation)

        self.collection(resource).add(rule.scope, rule.operation)

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
        return lambda *args, **kwargs: self.register_rule(name, *args,
                                                          **kwargs)

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
    def rule_exists_in_db(name: str, scope: Scope,
                          operation: Operation) -> bool:
        """Check if the rule exists in the DB.

        Parameters
        ----------
        name: str
            Name of the rule
        scope: Scope
            Scope of the rule
        operation: Operation
            Operation of the rule

        Returns
        -------
        bool
            Whenever this rule exists in the database or not
        """
        session = DatabaseSessionManager.get_session()
        result = session.query(Rule).filter_by(
            name=name,
            operation=operation,
            scope=scope
        ).scalar()
        session.commit()
        return result

    @staticmethod
    def check_user_rules(rules: list[Rule]) -> dict | bool:
        """
        Check if a user, node or container has all the `rules` in a list

        Parameters
        ----------
        rules: List[Rule]
            List of rules that user is checked to have

        Returns
        -------
        dict | bool
            Dict with a message which rule is missing, else None
        """
        for rule in rules:
            requires = RuleNeed(rule.name, rule.scope, rule.operation)
            try:
                Permission(requires).test()
            except PermissionDenied:
                return {"msg": f"You don't have the rule ({rule.name}, "
                        f"{rule.scope}, {rule.operation})"}
        return None
