from typing import List

from marshmallow import Schema, ValidationError, fields, validates
from marshmallow.validate import Length, Range

MAX_LEN_NAME = 128
MAX_LEN_STR_LONG = 1024


def validate_name(name: str) -> None:
    """
    Validate a name field in the request input.

    Parameters
    ----------
    name : str
        Name to validate.

    Raises
    ------
    ValidationError
        If the name is empty, too long or numerical
    """
    if not len(name):
        raise ValidationError("Name cannot be empty")
    if name.isnumeric():
        raise ValidationError("Name cannot a number")
    if len(name) > MAX_LEN_NAME:
        raise ValidationError(f"Name cannot be longer than {MAX_LEN_NAME} characters")


class _NameValidationSchema(Schema):
    """Schema for validating POST requests with a name field."""

    name = fields.String(required=True)

    @validates("name")
    def validate_name(self, name: str):
        """
        Validate the name in the input.

        Parameters
        ----------
        name : str
            Name to validate.

        Raises
        ------
        ValidationError
            If the name is empty, too long or numerical
        """
        validate_name(name)


class RoleInputSchema(_NameValidationSchema):
    """Schema for validating input for creating a role."""

    def __init__(self, default_roles: List[str]):
        super().__init__()
        self.default_roles = default_roles

    description = fields.String(validate=Length(max=MAX_LEN_STR_LONG))
    rules = fields.List(fields.Integer(validate=Range(min=1)), required=True)

    @validates("name")
    def validate_name(self, name: str):
        """
        Validate that role name is not one of the default roles.

        Parameters
        ----------
        name : str
            Role name to validate.

        Raises
        ------
        ValidationError
            If the role name is one of the default roles.
        """
        if name in self.default_roles:
            raise ValidationError("Role name cannot be one of the default roles")


class ServerRoleInputSchema(RoleInputSchema):
    """Schema for validating input for creating a server role."""

    organization_id = fields.Integer(validate=Range(min=1))
