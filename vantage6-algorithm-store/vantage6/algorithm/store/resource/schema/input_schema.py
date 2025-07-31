"""
Marshmallow schemas for validating input data for the API.
"""

import json

import marshmallow.validate as validate
from jsonschema import validate as json_validate
from marshmallow import Schema, ValidationError, fields, validates, validates_schema

from vantage6.common.enum import (
    AlgorithmArgumentType,
    AlgorithmStepType,
    AlgorithmViewPolicies,
)

from vantage6.algorithm.store.globals import ConditionalArgComparator
from vantage6.algorithm.store.model.common.enums import (
    Partitioning,
    VisualizationType,
)
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
    partitioning = fields.String(
        required=True, validate=validate.OneOf(Partitioning.list())
    )
    vantage6_version = fields.String(required=True)
    code_url = fields.String(required=True)
    documentation_url = fields.String()
    submission_comments = fields.String()
    functions = fields.Nested("FunctionInputSchema", many=True, required=True)


class AlgorithmPatchInputSchema(AlgorithmInputSchema):
    """
    Schema for the input of an algorithm.
    """

    refresh_digest = fields.Boolean(required=False)


class FunctionInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a function.
    """

    step_type = fields.String(
        required=True, validate=validate.OneOf(AlgorithmStepType.list())
    )
    display_name = fields.String(required=False)
    standalone = fields.Boolean(required=False)
    databases = fields.Nested("DatabaseInputSchema", many=True)
    arguments = fields.Nested("ArgumentInputSchema", many=True)
    ui_visualizations = fields.Nested("UIVisualizationInputSchema", many=True)

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
        # check that the conditional arguments are valid
        self._validate_conditional_values_and_types(arguments)
        # check that there are no circular conditions
        self._check_circular_conditions(arguments)

    @staticmethod
    def _validate_conditional_values_and_types(arguments: list[dict]) -> None:
        """
        Check that the conditional arguments are valid: they should have a value that
        matches the type of the argument that they are conditional on.

        Parameters
        ----------
        arguments : list[dict]
            List of arguments in the function

        Raises
        ------
        ValidationError
            If the conditional arguments are not valid
        """
        for argument in arguments:
            arg_name = argument.get("name")
            if not arg_name:
                # this will lead to error elsewhere but cannot proceed with this check
                raise ValidationError("Argument name is required")
            if conditional_on := argument.get("conditional_on"):
                # check that conditional_on argument exists
                if not any(arg["name"] == conditional_on for arg in arguments):
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on "
                        f"'{conditional_on}', but no other argument with that name "
                        "exists."
                    )
                elif conditional_on == arg_name:
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on itself."
                    )
                conditional_arg = next(
                    arg for arg in arguments if arg["name"] == conditional_on
                )
                # argument of list types cannot be conditional - this is not supported
                if conditional_arg.get("type_") in [
                    AlgorithmArgumentType.COLUMNS,
                    AlgorithmArgumentType.STRINGS,
                    AlgorithmArgumentType.INTEGERS,
                    AlgorithmArgumentType.FLOATS,
                    AlgorithmArgumentType.ORGANIZATIONS,
                ]:
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on "
                        f"'{conditional_on}', but the conditional argument is of a list"
                        " type, which is not supported."
                    )
                elif conditional_arg.get("type_") in [
                    AlgorithmArgumentType.ORGANIZATION,
                    AlgorithmArgumentType.JSON,
                ]:
                    raise ValidationError(
                        f"The argument '{arg_name}' is conditional on "
                        f"'{conditional_on}', but the conditional argument is of type "
                        f"'{conditional_arg.get('type_')}', which is not supported."
                    )
                # check that the conditional value matches the type of the argument
                # that the argument is conditional on
                conditional_value = argument.get("conditional_value")
                conditional_type = conditional_arg.get("type_")
                if not conditional_type:
                    raise ValidationError(
                        f"Type of conditional argument '{conditional_on}' is not set"
                    )
                if not conditional_value:
                    # conditional value is null - this is allowed and does not need to
                    # be checked further
                    continue
                elif conditional_type == AlgorithmArgumentType.INTEGER:
                    try:
                        int(conditional_value)
                    except (ValueError, TypeError) as exc:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            f"integer, while the conditional argument '{conditional_on}' "
                            "requires an integer"
                        ) from exc
                elif conditional_type == AlgorithmArgumentType.FLOAT:
                    try:
                        float(conditional_value)
                    except (ValueError, TypeError) as exc:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            f"float, while the conditional argument '{conditional_on}' "
                            "requires a float"
                        ) from exc
                elif conditional_type == AlgorithmArgumentType.BOOLEAN:
                    if conditional_value.lower() not in ["true", "false", "1", "0"]:
                        raise ValidationError(
                            f"Conditional value '{conditional_value}' is not a valid "
                            "boolean, while the conditional argument "
                            f"'{conditional_on}' requires a boolean. Please use 'true',"
                            " 'false', '1', or '0'"
                        )

    @staticmethod
    def _check_circular_conditions(arguments: list[dict]) -> None:
        """
        Check that there are no circular conditions in conditional arguments.

        Parameters
        ----------
        arguments : list[dict]
            List of arguments in the function

        Raises
        ------
        ValidationError
            If there are circular conditions
        """
        # make list of all conditional arguments
        conditions = []
        for argument in arguments:
            if conditional_on := argument.get("conditional_on"):
                conditions.append((argument["name"], conditional_on))
        # check for circular conditions. Since one argument can only be dependent on one
        # other argument, we can check for circular conditions by following the chain of
        # conditions until we reach the first condition again. If we reach the first
        # condition again, there is a circular condition.
        # note that we already check in function above that name != conditional_on.
        for condition in conditions:
            first_condition = condition
            first_iteration = True
            condition_chain = [condition[0]]
            while first_iteration or condition != first_condition:
                first_iteration = False
                condition = next((c for c in conditions if c[0] == condition[1]), None)
                if not condition:
                    break
                condition_chain.append(condition[0])
            if condition == first_condition:
                raise ValidationError(
                    "Circular conditional arguments detected: "
                    f"{' -> '.join(condition_chain)}"
                )


class DatabaseInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a database.
    """

    # databases have a name and optional description so we can use the
    # _NameDescriptionSchema
    multiple = fields.Boolean(required=False, default=False)


class _MixedBaseTypeField(fields.Field):
    """
    Field that can be used to validate a field that can be str, int or float
    """

    def _deserialize(self, value, attr, data, **kwargs):
        if isinstance(value, str) or isinstance(value, int) or isinstance(value, float):
            return value
        else:
            raise ValidationError("Values should be str, int or float")


class ArgumentInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of an argument.
    """

    display_name = fields.String()
    type_ = fields.String(
        required=True,
        data_key="type",
        validate=validate.OneOf(AlgorithmArgumentType.list()),
    )
    allowed_values = fields.List(_MixedBaseTypeField())
    has_default_value = fields.Boolean()
    default_value = fields.String()
    conditional_on = fields.String()
    conditional_operator = fields.String(
        validate=validate.OneOf(ConditionalArgComparator.list())
    )
    conditional_value = fields.String()
    is_frontend_only = fields.Boolean()

    @validates_schema
    def validate_schema(self, data, **kwargs):
        """
        Validate that
        - if the default value is present, has_default_value is True,
        - if the default value is given, that it matches the type
        - No conditionals are provided if the argument must always be specified
        - That if one of the conditional fields is specified, all are specified
        """
        if data.get("default_value") and not data.get("has_default_value"):
            raise ValidationError(
                "Default value cannot be given if has_default_value is False"
            )
        if data.get("conditional_on") and not data.get("has_default_value"):
            raise ValidationError(
                "Variable cannot be conditional on another variable if it has no "
                "default: arguments without defaults must always be specified"
            )
        # Check that all required conditional fields are specified or none. Note that
        # the conditional_value is optional, as it may be null.
        conditional_fields = [
            "conditional_on",
            "conditional_operator",
        ]
        specified_conditionals = [
            field for field in conditional_fields if data.get(field)
        ]
        if specified_conditionals and len(specified_conditionals) != len(
            conditional_fields
        ):
            raise ValidationError(
                "Either all conditional fields must be specified or none of them should"
                " be specified"
            )
        # if default value is given, validate that it matches the type
        type_ = data.get("type_")
        if default := data.get("default_value"):
            if (
                type_ == AlgorithmArgumentType.INTEGER
                or type_ == AlgorithmArgumentType.ORGANIZATION
            ):
                try:
                    int(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid integer, while the "
                        f"argument type {type_} requires an integer"
                    ) from exc
            elif type_ == AlgorithmArgumentType.FLOAT:
                try:
                    float(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid float, while the "
                        f"argument type {type_} requires a float"
                    ) from exc
            elif type_ == AlgorithmArgumentType.BOOLEAN:
                if str(default).lower() not in ["true", "false", "1", "0"]:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid boolean, while the "
                        f"argument type {type_} requires a boolean. Please use 'true', "
                        "'false', '1', or '0'"
                    )
            elif type_ == AlgorithmArgumentType.JSON:
                try:
                    json.loads(default)
                except ValueError as exc:
                    raise ValidationError(
                        f"Default value '{default}' is not a valid JSON object, while "
                        f"the argument type {type_} requires a JSON object"
                    ) from exc
            elif (
                type_ == AlgorithmArgumentType.STRINGS
                or type_ == AlgorithmArgumentType.COLUMNS
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
                type_ == AlgorithmArgumentType.INTEGERS
                or type_ == AlgorithmArgumentType.ORGANIZATIONS
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
            elif type_ == AlgorithmArgumentType.FLOATS:
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

        # if there are allowed values, validate that they are of the correct type
        if data.get("allowed_values"):
            if type_ == AlgorithmArgumentType.INTEGER:
                desired_type = int
            elif type_ == AlgorithmArgumentType.FLOAT:
                desired_type = float
            else:
                desired_type = str
            for value in data.get("allowed_values"):
                try:
                    desired_type(value)
                except (ValueError, TypeError):
                    raise ValidationError(
                        f"Allowed values should be of type {desired_type} because the "
                        f"argument type is {type_}"
                    )

        # if there are both allowed values and a default value, validate that the
        # default value is one of the allowed values
        if data.get("default_value") and data.get("allowed_values"):
            if data.get("default_value") not in data.get("allowed_values"):
                raise ValidationError("Default value is not one of the allowed values")


class UIVisualizationInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a UI visualization.
    """

    type_ = fields.String(
        required=True,
        data_key="type",
        validate=validate.OneOf(VisualizationType.list()),
    )
    schema = fields.Dict()

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

    organization_id = fields.Integer()
    roles = fields.List(fields.Integer(validate=validate.Range(min=1)))


class PolicyInputSchema(Schema):
    """
    Schema for the input of policies.

    Note that the keys in this schema should match the values in the Policies enum.
    The Policies enum is for convenience to check against the keys.
    """

    algorithm_view = fields.String(
        validate=validate.OneOf(AlgorithmViewPolicies.list())
    )


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
