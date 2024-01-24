from marshmallow import Schema, fields, ValidationError, validates

from vantage6.algorithm.store.model.common.enums import (
    Partitioning,
    FunctionType,
    ArgumentType,
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
    functions = fields.Nested("FunctionInputSchema", many=True, required=True)

    @validates("partitioning")
    def validate_partitioning(self, value):
        """
        Validate that the partitioning is one of the allowed values.
        """
        types = [p.value for p in Partitioning]
        if value not in types:
            raise ValidationError(
                f"Partitioning '{value}' is not one of the allowed values " f"{types}"
            )


class FunctionInputSchema(_NameDescriptionSchema):
    """
    Schema for the input of a function.
    """

    type = fields.String(required=True)
    databases = fields.Nested("DatabaseInputSchema", many=True)
    arguments = fields.Nested("ArgumentInputSchema", many=True)

    @validates("type")
    def validate_type(self, value):
        """
        Validate that the type is one of the allowed values.
        """
        types = [f.value for f in FunctionType]
        if value not in types:
            raise ValidationError(
                f"Function type '{value}' is not one of the allowed values " f"{types}"
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

    type = fields.String(required=True)

    @validates("type")
    def validate_type(self, value):
        """
        Validate that the type is one of the allowed values.
        """
        types = [a.value for a in ArgumentType]
        if value not in types:
            raise ValidationError(
                f"Argument type '{value}' is not one of the allowed values " f"{types}"
            )


class Vantage6ServerInputSchema(Schema):
    """
    Schema for the input of a vantage6 server.
    """

    url = fields.String(required=True)
    force = fields.Boolean()
