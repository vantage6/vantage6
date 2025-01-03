"""
Marshmallow schemas for validating input data for the API.
"""

import json
from marshmallow import Schema, fields, ValidationError, validates, validates_schema
import marshmallow.validate as validate
from jsonschema import validate as json_validate

from vantage6.common.enum import AlgorithmViewPolicies
from vantage6.algorithm.store.model.common.enums import (
    Partitioning,
    FunctionType,
    ArgumentType,
    VisualizationType,
)
from vantage6.algorithm.store.globals import ConditionalArgComparator
from vantage6.algorithm.store.model.common.ui_visualization_schemas import (
    get_schema_for_visualization,
)


class _NameDescriptionSchema(Schema):
    """
    Schema for the name and description fields.
    """

    name = fields.String(required=True)
    description = fields.String()


class AlgorithmInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of an algorithm.
    """

    image = fields.String(required=True)
    partitioning = fields.String(required=True)
    vantage6_version = fields.String(required=True)
    code_url = fields.String(required=True)
    documentation_url = fields.String()
    functions = fields.Nested("FunctionInputSchema", many=True, required=True)

    @validates("partitioning")
    def validate_partitioning(self, value):
        """
        Validate that the partitioning is one of the allowed values.
        """
        types = [p.value for p in Partitioning]
        if value not in types:
            raise ValidationError(
                f"Partitioning '{value}' is not one of the allowed values {types}"
            )


class AlgorithmPatchInputSchema(AlgorithmInputSchema):
    """
    Schema for the input of an algorithm.
    """

    refresh_digest = fields.Boolean(required=False)


class FunctionInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a function.
    """

    type_ = fields.String(required=True, data_key="type")
    display_name = fields.String(required=False)
    databases = fields.Nested("DatabaseInputSchema", many=True)
    arguments = fields.Nested("ArgumentInputSchema", many=True)
    ui_visualizations = fields.Nested("UIVisualizationInputSchema", many=True)

    @validates("type_")
    def validate_type(self, value):
        """
        Validate that the type is one of the allowed values.
        """
        types = [f.value for f in FunctionType]
        if value not in types:
            raise ValidationError(
                f"Function type '{value}' is not one of the allowed values {types}"
            )

    @validates_schema
    def validate_conditional_arguments(self, data, **kwargs):
        """
        Validate that the conditional arguments are valid.
        """
        arguments = data.get("arguments")
        if not arguments:
            return
        # check that all arguments have a unique name - they cannot have the same name
        # because they are used as keys in the function arguments
        names = [arg.get("name") for arg in arguments]
        if len(names) != len(set(names)):
            raise ValidationError("All arguments must have a unique name")
        for argument in arguments:
            arg_name = argument.get("name")
            if not arg_name:
                # this will lead to error elsewhere but cannot proceed with this check
                continue
            if conditional_on := argument.get("conditional_on"):
                if not any(arg["name"] == conditional_on for arg in arguments):
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on "
                        f"'{conditional_on}', but no other argument with that name "
                        "exists."
                    )
                conditional_arg = next(
                    arg for arg in arguments if arg["name"] == conditional_on
                )
                # argument of list types cannot be conditional - this is not supported
                if conditional_arg.get("type_") in [
                    ArgumentType.COLUMNS.value,
                    ArgumentType.STRINGS.value,
                    ArgumentType.INTEGERS.value,
                    ArgumentType.FLOATS.value,
                    ArgumentType.ORGANIZATIONS.value,
                ]:
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on "
                        f"'{conditional_on}', but the conditional argument is of a list"
                        " type, which is not supported."
                    )
                # check that the conditional value matches the type of the argument
                # that the argument is conditional on
                conditional_value = argument.get("conditional_value")
                conditional_type = conditional_arg.get("type_")
                if not conditional_type:
                    continue  # this will lead to error elsewhere but cannot proceed
                if (
                    conditional_type == ArgumentType.INTEGER.value
                    or conditional_type == ArgumentType.ORGANIZATION.value
                ):
                    try:
                        int(conditional_value)
                    except ValueError as exc:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            f"integer, while the conditional argument '{conditional_on}' "
                            "requires an integer"
                        ) from exc
                elif conditional_type == ArgumentType.FLOAT.value:
                    try:
                        float(conditional_value)
                    except ValueError as exc:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            f"float, while the conditional argument '{conditional_on}' "
                            "requires a float"
                        ) from exc
                elif conditional_type == ArgumentType.BOOLEAN.value:
                    if conditional_value.lower() not in ["true", "false", "1", "0"]:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            "boolean, while the conditional argument "
                            f"'{conditional_on}' requires a boolean. Please use 'true',"
                            " 'false', '1', or '0'"
                        )


class DatabaseInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a database.
    """

    # databases only have a name and optional description so we can use the
    # _NameDescriptionSchema


class ArgumentInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of an argument.
    """

    display_name = fields.String()
    type_ = fields.String(required=True, data_key="type")
    has_default_value = fields.Boolean()
    default_value = fields.String()
    conditional_on = fields.String()
    conditional_comparator = fields.String()
    conditional_value = fields.String()

    @validates("type_")
    def validate_type(self, value):
        """
        Validate that the type is one of the allowed values.
        """
        types = [a.value for a in ArgumentType]
        if value not in types:
            raise ValidationError(
                f"Argument type '{value}' is not one of the allowed values: {types}"
            )

    @validates("conditional_comparator")
    def validate_conditional_comparator(self, value):
        """
        Validate that the conditional comparator is one of the allowed values.
        """
        comparators = [c.value for c in ConditionalArgComparator]
        if value not in comparators:
            raise ValidationError(
                f"Conditional comparator '{value}' is not one of the allowed values: "
                f"{comparators}"
            )

    @validates_schema
    def validate_default_value(self, data, **kwargs):
        """
        Validate that if the default value is present, has_default_value is True, and
        check, if the default value is given, that it matches the type
        """
        if data.get("default_value") and not data.get("has_default_value"):
            raise ValidationError(
                "Default value cannot be given if has_default_value is False"
            )
        # if default value is given, validate that it matches the type
        if default := data.get("default_value"):
            type_ = data.get("type_")
            if (
                type_ == ArgumentType.INTEGER.value
                or type_ == ArgumentType.ORGANIZATION.value
            ):
                try:
                    int(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid integer, while the "
                        f"argument type {type_} requires an integer"
                    ) from exc
            elif type_ == ArgumentType.FLOAT.value:
                try:
                    float(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid float, while the "
                        f"argument type {type_} requires a float"
                    ) from exc
            elif type_ == ArgumentType.BOOLEAN.value:
                if str(default).lower() not in ["true", "false", "1", "0"]:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid boolean, while the "
                        f"argument type {type_} requires a boolean. Please use 'true', "
                        "'false', '1', or '0'"
                    )
            elif type_ == ArgumentType.JSON.value:
                try:
                    json.loads(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid JSON object, while "
                        f"the argument type {type_} requires a JSON object"
                    ) from exc
            elif (
                type_ == ArgumentType.STRINGS.value
                or type_ == ArgumentType.COLUMNS.value
            ):
                try:
                    json_list = json.loads(default)
                    if not isinstance(json_list, list):
                        raise ValueError(f"Not a list: {json_list}")
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid JSON array, while "
                        f"the argument type {type_} requires a JSON array"
                    ) from exc
            elif (
                type_ == ArgumentType.INTEGERS.value
                or type_ == ArgumentType.ORGANIZATIONS.value
            ):
                try:
                    json_list = json.loads(default)
                    if not isinstance(json_list, list):
                        raise ValueError(f"Not a list: {json_list}")
                    for value in json_list:
                        int(value)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid JSON array of "
                        f"integers, while the argument type {type_} requires a JSON "
                        "array of integers"
                    ) from exc
            elif type_ == ArgumentType.FLOATS.value:
                try:
                    json_list = json.loads(default)
                    if not isinstance(json_list, list):
                        raise ValueError(f"Not a list: {json_list}")
                    for value in json_list:
                        float(value)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid JSON array of "
                        f"floats, while the argument type {type_} requires a JSON array"
                        " of floats"
                    ) from exc


class UIVisualizationInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a UI visualization.
    """

    type_ = fields.String(required=True, data_key="type")
    schema = fields.Dict()

    @validates("type_")
    def validate_type(self, value):
        """
        Validate that the type is one of the allowed values.
        """
        types = [v.value for v in VisualizationType]
        if value not in types:
            raise ValidationError(
                f"UI visualization type '{value}' is not one of the allowed values "
                f"{types}"
            )

    @validates_schema
    def validate_schema(self, data, **kwargs):
        """
        Validate that the schema is a valid JSON schema.
        """
        schema = data.get("schema")
        type_ = data.get("type_")
        if schema and type_:
            try:
                json_validate(schema, get_schema_for_visualization(type_))
            except Exception as exc:
                raise ValidationError(
                    "Schema does not match requirements for that visualization type: "
                    f"{exc}",
                ) from exc


class UserInputSchema(Schema):
    """Schema for validating input for creating a user."""

    username = fields.String(required=True)
    roles = fields.List(fields.Integer(validate=validate.Range(min=1)))


class UserUpdateInputSchema(Schema):
    """Schema for validating input for updating a user."""

    # separate schema for PATCH /user: we don't allow updating the username, email is
    # retrieved automatically in POST /user. Finally, there is an additional field to
    # update the email from the server
    email = fields.Email()
    roles = fields.List(fields.Integer(validate=validate.Range(min=1)))
    update_email = fields.Boolean()

    @validates_schema
    def validate_email(self, data, **kwargs):
        """
        Validate that the email is not present when update_email is True.
        """
        if data.get("update_email") and data.get("email"):
            raise ValidationError(
                "Both options 'email' and 'update_email' are present, but only one "
                "can be used simultaneously, since 'update_email' is a flag to update "
                "the email with the value from the vantage6 server."
            )


class Vantage6ServerInputSchema(Schema):
    """
    Schema for the input of a vantage6 server.
    """

    url = fields.String(required=True)
    force = fields.Boolean()


class PolicyInputSchema(Schema):
    """
    Schema for the input of policies.

    Note that the keys in this schema should match the values in the Policies enum.
    The Policies enum is for convenience to check against the keys.
    """

    algorithm_view = fields.String(
        validate=validate.OneOf([p.value for p in AlgorithmViewPolicies])
    )
    allowed_servers = fields.List(fields.String())
    allow_localhost = fields.Boolean()


class ReviewCreateInputSchema(Schema):
    """
    Schema for creating a new review
    """

    reviewer_id = fields.Integer(required=True, validate=validate.Range(min=1))
    algorithm_id = fields.Integer(required=True, validate=validate.Range(min=1))


class ReviewUpdateInputSchema(Schema):
    """
    Schema for updating a review by a reviewer
    """

    comment = fields.String()
