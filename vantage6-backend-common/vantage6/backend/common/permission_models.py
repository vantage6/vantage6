from __future__ import annotations

from typing import Any


class RuleInterface:
    name: Any
    operation: Any
    description: Any

    @classmethod
    def get_by_(cls, *args, **kwargs):
        raise NotImplementedError("get_by_ method must be implemented for Rule class")

    def __repr__(self) -> str:
        """
        String representation of the rule.

        Returns
        -------
        str
            String representation of the rule
        """
        raise NotImplementedError("__repr__ method must be implemented for Rule class")


class RoleInterface:
    name: Any
    description: Any
    rules: Any
    users: Any

    def __repr__(self) -> str:
        """
        String representation of the role.

        Returns
        -------
        str
            String representation of the role
        """
        raise NotImplementedError("__repr__ method must be implemented for Role class")
