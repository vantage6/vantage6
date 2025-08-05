from __future__ import annotations

import importlib
import logging
from abc import ABC, abstractmethod
from enum import EnumMeta
from typing import NamedTuple

from flask_principal import Permission

from vantage6.common import logger_name

from vantage6.backend.common.permission_models import RuleInterface

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

RuleNeed = NamedTuple("RuleNeed", [("name", str), ("scope", str), ("operation", str)])


def get_attribute_name(
    operation: str, scope: str | None = None, shorten: bool = True
) -> str:
    """
    Get the attribute name for a rule.

    Parameters
    ----------
    operation: str
        Operation of the rule
    scope: str | None
        Scope of the rule
    shorten: bool
        Whether to shorten the attribute name in the format of 'v_glo' for view global.
        If False, the attribute name will be the full operation name.

    Returns
    -------
    str
        Attribute name for the rule
    """
    if shorten:
        attribute_name = operation[0].lower()
        if scope:
            attribute_name += f"_{scope[0:3].lower()}"
    else:
        attribute_name = operation
    return attribute_name


class RuleCollectionBase(ABC, dict):
    """
    Class that tracks a set of all rules for a certain resource name

    Parameters
    ----------
    name: str
        Name of the resource endpoint (e.g. node, organization, user)
    """

    def __init__(self, name):
        self.name = name

    def add(
        self, operation: str, scope: str | None = None, shorten: bool = True
    ) -> None:
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

        attribute_name = get_attribute_name(operation, scope, shorten)
        self.__setattr__(attribute_name, permission)


class PermissionManagerBase(ABC):
    """
    Loads the permissions and syncs rules in database with rules defined in
    the code
    """

    def __init__(
        self, resources_location: str, resources: list[str], default_roles: EnumMeta
    ) -> None:
        self.collections: dict[str, RuleCollectionBase] = {}
        self.default_roles = default_roles
        log.info("Loading permission system...")
        self.load_rules_from_resources(resources_location, resources)

    @abstractmethod
    def assign_rule_to_fixed_role(self, *args, **kwargs) -> None:
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
        pass

    @abstractmethod
    def register_rule(self, *args, **kwargs) -> None:
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
        rules: list[RuleInterface]
            List of rules that user is checked to have

        Returns
        -------
        dict | None
            Dict with a message which rule is missing, else None
        """
        pass

    @abstractmethod
    def get_new_collection(self, name: str) -> RuleCollectionBase:
        """
        Initialize and return a new RuleCollection.
        Parameters
        ----------
        name: str
            Name of the collection

        Returns
        -------
        RuleCollectionBase
            New RuleCollection
        """
        pass

    def load_rules_from_resources(
        self, resources_location: str, resources: list[str]
    ) -> None:
        """
        Collect all permission rules from all registered API resources.

        Parameters
        ----------
        resources_location: str
            Name of the module where to load the resources from (e.g. vantage6.server.resource).

        resources: list[str]
            List of the resources to load.
        """
        for res in resources:
            module = importlib.import_module(f"{resources_location}.{res}")
            try:
                module.permissions(self)
            except Exception:
                module_name = module.__name__.split(".")[-1]
                log.debug(
                    "Resource '%s' contains no or invalid permissions", module_name
                )

    def assign_rule_to_root(self, *args, **kwargs) -> None:
        """
        Assign a rule to the root role.

        Parameters
        ----------
        resource: str
            Resource that the rule applies to
        operation: Operation
            Operation that the rule applies to
        scope: Scope
            Scope that the rule applies to
        """

        self.assign_rule_to_fixed_role(self.default_roles.ROOT.value, *args, **kwargs)

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

    def collection(self, name: str) -> RuleCollectionBase:
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
        RuleCollectionBase
            The collection of rules belonging to the module name
        """
        if self._collection_exists(name):
            return self.collections[name]
        else:
            self.collections[name] = self.get_new_collection(name)
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

    def __getattr__(self, name: str) -> RuleCollectionBase:
        try:
            collection = self.collections[name]
            return collection
        except Exception as e:
            log.critical(f"Missing permission collection! {name}")
            raise e
