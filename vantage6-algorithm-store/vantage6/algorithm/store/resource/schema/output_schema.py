from marshmallow import fields

from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.server.resource.common.output_schema import BaseHATEOASModelSchema


class HATEOASModelSchema(BaseHATEOASModelSchema):
    """
    This class is used to convert foreign-key fields to HATEOAS specification.
    """

    def __init__(self, *args, **kwargs) -> None:
        # set lambda functions to create links for one to one relationship
        # TODO check if all below are used
        setattr(self, "algorithm", lambda obj: self.create_hateoas("algorithm", obj))
        setattr(self, "function", lambda obj: self.create_hateoas("function", obj))
        setattr(self, "database", lambda obj: self.create_hateoas("database", obj))
        setattr(self, "argument", lambda obj: self.create_hateoas("argument", obj))

        # call super class. Do this after setting the attributes above, because
        # the super class initializer will call the attributes.
        super().__init__(*args, **kwargs)


class AlgorithmOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Algorithm

    functions = fields.Nested("FunctionOutputSchema", many=True, exclude=["id"])


class FunctionOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Function
        exclude = ["type_"]

    type = fields.String(attribute="type_")

    databases = fields.Nested("DatabaseOutputSchema", many=True, exclude=["id"])
    arguments = fields.Nested("ArgumentOutputSchema", many=True, exclude=["id"])


class DatabaseOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Database


class ArgumentOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Argument
        exclude = ["type_"]

    type = fields.String(attribute="type_")


class Vantage6ServerOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Vantage6Server
