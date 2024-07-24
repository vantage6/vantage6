"""
Marshmallow schemas for validating input data for the API.
"""

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

    type_ = fields.String(required=True, data_key="type")

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

    roles = fields.List(fields.Integer(validate=validate.Range(min=1)))
    username = fields.String()


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
