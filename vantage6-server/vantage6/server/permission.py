import logging
import importlib

from collections import namedtuple
from flask_principal import Permission

from vantage6.server.globals import RESOURCES
from vantage6.server.default_roles import DefaultRole
from vantage6.server.model.base import Base
from vantage6.server.model.role import Role
from vantage6.server.model.rule import Rule, Operation, Scope
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.utils import obtain_auth_collaborations, obtain_auth_organization
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = namedtuple("RuleNeed", ["name", "scope", "operation"])


# TODO BvB 2023-07-27 this utility is a bit superfluous with the definition
# of the operation and scope enums. We should remove it but then add longer
# values to the enums, which leads to many other changes
def print_operation(operation: Operation) -> str:
    """
    String representation of the operation, that is readable by humans.

    Parameters
    ----------
    operation : Operation
        Operation to be printed

    Returns
    -------
    str
        String representation of the operation

    Raises
    ------
    ValueError
        If the operation is not known
    """
    if operation.VIEW:
        return "view"
    elif operation.EDIT:
        return "edit"
    elif operation.CREATE:
        return "create"
    elif operation.DELETE:
        return "delete"
    elif operation.SEND:
        return "send"
    elif operation.RECEIVE:
        return "receive"
    else:
        raise ValueError(f"Unknown operation {operation}")


def print_scope(scope: Scope) -> str:
    """
    String representation of the scope, that is readable by humans.

    Parameters
    ----------
    scope : Scope
        Scope to be printed

    Returns
    -------
    str
        String representation of the scope

    Raises
    ------
    ValueError
        If the scope is not known
    """
    if scope.ORGANIZATION:
        return "organization"
    elif scope.COLLABORATION:
        return "collaboration"
    elif scope.GLOBAL:
        return "global"
    elif scope.OWN:
        return "own"
    else:
        raise ValueError(f"Unknown scope {scope}")


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
        self.__setattr__(f"{operation}_{scope}", permission)

    def can_for_org(self, operation: Operation, subject_org_id: int | str) -> bool:
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
        global_perm = getattr(self, f"{operation}_{Scope.GLOBAL}")
        if global_perm and global_perm.can():
            return True

        # check if the entity has organization permission and organization is
        # the same as the subject organization
        org_perm = getattr(self, f"{operation}_{Scope.ORGANIZATION}")
        if auth_org.id == subject_org_id and org_perm and org_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # organization is in the collaboration of the own organization
        col_perm = getattr(self, f"{operation}_{Scope.COLLABORATION}")
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
        global_perm = getattr(self, f"{operation}_{Scope.GLOBAL}")
        if global_perm and global_perm.can():
            return True

        # check if the entity has collaboration permission and the subject
        # collaboration is in the collaborations of the user/node
        col_perm = getattr(self, f"{operation}_{Scope.COLLABORATION}")
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
        if getattr(self, f"{operation}_{Scope.GLOBAL}"):
            return Scope.GLOBAL
        elif getattr(self, f"{operation}_{Scope.COLLABORATION}"):
            return Scope.COLLABORATION
        elif getattr(self, f"{operation}_{Scope.ORGANIZATION}"):
            return Scope.ORGANIZATION
        elif getattr(self, f"{operation}_{Scope.OWN}"):
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
            module = importlib.import_module("vantage6.server.resource." + res)
            try:
                module.permissions(self)
            except Exception:
                module_name = module.__name__.split(".")[-1]
                log.debug(
                    f"Resource '{module_name}' contains no or invalid permissions"
                )

    def assign_rule_to_root(
        self, name: str, scope: Scope, operation: Operation
    ) -> None:
        """
        Assign a rule to the root role.

        resource: str
            Resource that the rule applies to
        scope: Scope
            Scope that the rule applies to
        operation: Operation
            Operation that the rule applies to
        """
        self.assign_rule_to_fixed_role(DefaultRole.ROOT, name, scope, operation)

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
        self.assign_rule_to_fixed_role(DefaultRole.NODE, resource, scope, operation)

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
            DefaultRole.CONTAINER, resource, scope, operation
        )

    @staticmethod
    def assign_rule_to_fixed_role(
        fixedrole: str, resource: str, scope: Scope, operation: Operation
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

        rule = Rule.get_by_(resource, scope, operation)
        if not rule:
            log.error(f"Rule ({resource},{scope},{operation}) not found!")

        if rule not in role.rules:
            role.rules.append(rule)
            log.info(
                f"Rule ({resource},{scope},{operation}) added to " f"{fixedrole} role!"
            )

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
            rule = Rule(
                name=resource, operation=operation, scope=scope, description=description
            )
            rule.save()
            log.debug(
                f"New auth rule '{resource}' with scope={scope}"
                f" and operation={operation} is stored in the DB"
            )

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
    def rule_exists_in_db(name: str, scope: Scope, operation: Operation) -> bool:
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
        result = (
            session.query(Rule)
            .filter_by(name=name, operation=operation, scope=scope)
            .scalar()
        )
        session.commit()
        return result

    def check_user_rules(self, rules: list[Rule]) -> dict | None:
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
                    f"{print_scope(rule.scope)}, "
                    f"{print_operation(rule.operation)})"
                }
        return None
