from marshmallow import fields
from flask import url_for

from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model import Base
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.server.resource.common.output_schema import (
    BaseHATEOASModelSchema
)


def create_one_to_many_link(obj: Base, link_to: str, link_from: str) -> str:
    """
    Create an API link to get objects related to a given object.

    Parameters
    ----------
    obj : Base
        Object to which the link is created
    link_to : str
        Name of the resource to which the link is created
    link_from : str
        Name of the resource from which the link is created

    Returns
    -------
    str
        API link

    Examples
    --------
    >>> create_one_to_many_link(obj, "node", "organization_id")
    "/api/node?organization_id=<obj.id>"
    """
    endpoint = link_to + "_without_id"
    values = {link_from: obj.id}
    return url_for(endpoint, **values)


class HATEOASModelSchema(BaseHATEOASModelSchema):
    """
    This class is used to convert foreign-key fields to HATEOAS specification.
    """
    def __init__(self, *args, **kwargs) -> None:

        # set lambda functions to create links for one to one relationship
        # TODO check if all below are used
        setattr(self, "algorithm",
                lambda obj: self.create_hateoas("algorithm", obj))
        setattr(self, "function",
                lambda obj: self.create_hateoas("function", obj))
        setattr(self, "database",
                lambda obj: self.create_hateoas("database", obj))
        setattr(self, "argument",
                lambda obj: self.create_hateoas("argument", obj))
        setattr(self, "rule",
                lambda obj: self.create_hateoas("rule", obj))
        setattr(self, "role",
                lambda obj: self.create_hateoas("role", obj))

        # call super class. Do this after setting the attributes above, because
        # the super class initializer will call the attributes.
        super().__init__(*args, **kwargs)


class AlgorithmOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Algorithm

    functions = fields.Nested(
        'FunctionOutputSchema', many=True, exclude=['id']
    )


class FunctionOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Function

    databases = fields.Nested(
        'DatabaseOutputSchema', many=True, exclude=['id']
    )
    arguments = fields.Nested(
        'ArgumentOutputSchema', many=True, exclude=['id']
    )


class DatabaseOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Database


class ArgumentOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Argument


class Vantage6ServerOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Vantage6Server


class RoleOutputSchema(HATEOASModelSchema):

    rules = fields.Function(lambda obj: create_one_to_many_link(
        obj, link_to='rule', link_from='role_id'
    ))

    class Meta:
        model = Role


class RuleOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Rule
        exclude = ('roles',)
