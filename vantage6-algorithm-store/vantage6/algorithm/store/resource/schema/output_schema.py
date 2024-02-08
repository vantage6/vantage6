from marshmallow import fields
from flask import url_for

from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model import Base
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.server.resource.common.output_schema import BaseHATEOASModelSchema


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
        setattr(self, "user",
                lambda obj: self.create_hateoas("user", obj))
        setattr(self, "review",
                lambda obj: self.create_hateoas("review", obj))

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


class UserSchema(HATEOASModelSchema):

    class Meta:
        model = User

    roles = fields.Function(lambda obj: create_one_to_many_link(
        obj, link_to='role', link_from='user_id'
    ))
    rules = fields.Function(lambda obj: create_one_to_many_link(
        obj, link_to='rule', link_from='user_id'
    ))
    algorithm = fields.Function(lambda obj: create_one_to_many_link(
        obj, link_to='algorithm', link_from='user_id'
    ))


class Review(HATEOASModelSchema):

    class Meta:
        model = Review

    reviewers = fields.Function(lambda obj: create_one_to_many_link(
        obj, link_to='user_id', link_from='review'
    ))


# class UserWithPermissionDetailsSchema(UserSchema):
#     """
#     A schema for API responses that contains regular user details plus
#     additional permission details for the user to be used by the UI.
#     """
#     permissions = fields.Method("permissions_")
#
#     @staticmethod
#     def permissions_(obj: User) -> dict:
#         """
#         Returns a dictionary containing permission details for the user to be
#         used by the UI.
#
#         Parameters
#         ----------
#         obj : User
#             The user to get permission details for.
#
#         Returns
#         -------
#         dict
#             A dictionary containing permission details for the user.
#         """
#         role_ids = [role.id for role in obj.roles]
#         rule_ids = list(set(
#             [rule.id for rule in obj.rules] + \
#             [rule.id for role in obj.roles for rule in role.rules]
#         ))
#
#         return {
#             "roles": role_ids,
#             "rules": rule_ids
#         }
