from marshmallow import fields

from vantage6.backend.common.resource.output_schema import (
    BaseHATEOASModelSchema,
    create_one_to_many_link,
)
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.ui_visualization import UIVisualization
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server


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
        setattr(self, "rule", lambda obj: self.create_hateoas("rule", obj))
        setattr(self, "role", lambda obj: self.create_hateoas("role", obj))
        setattr(self, "user", lambda obj: self.create_hateoas("user", obj))
        setattr(self, "review", lambda obj: self.create_hateoas("review", obj))
        setattr(self, "server", lambda obj: self.create_hateoas("server", obj))

        # call super class. Do this after setting the attributes above, because
        # the super class initializer will call the attributes.
        super().__init__(*args, **kwargs)


class AlgorithmOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the Algorithm model"""

    class Meta:
        model = Algorithm

    functions = fields.Nested("FunctionOutputSchema", many=True)
    developer_id = fields.Integer(data_key="developer_id")
    reviews = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="review", link_from="algorithm_id"
        )
    )


class FunctionOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the Function model"""

    class Meta:
        model = Function

    type_ = fields.String(data_key="type")

    databases = fields.Nested("DatabaseOutputSchema", many=True)
    arguments = fields.Nested("ArgumentOutputSchema", many=True)
    ui_visualizations = fields.Nested("UIVisualizationOutputSchema", many=True)


class DatabaseOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the Database model"""

    class Meta:
        model = Database


class ArgumentOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the Argument model"""

    class Meta:
        model = Argument

    type_ = fields.String(data_key="type")
    conditional_on_id = fields.Integer()


class UIVisualizationOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the UIVisualization model"""

    class Meta:
        model = UIVisualization

    type_ = fields.String(data_key="type")


class Vantage6ServerOutputSchema(HATEOASModelSchema):
    """Marshmallow output schema to serialize the Vantage6Server model"""

    class Meta:
        model = Vantage6Server

    users = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="user", link_from="v6_server_id"
        )
    )


class RoleOutputSchema(HATEOASModelSchema):
    rules = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="rule", link_from="role_id")
    )
    users = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="user", link_from="role_id")
    )

    class Meta:
        model = Role


class RuleOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Rule
        exclude = ("roles",)


class UserOutputSchema(HATEOASModelSchema):
    class Meta:
        model = User

    roles = fields.Function(
        lambda obj: create_one_to_many_link(obj, link_to="role", link_from="user_id")
    )
    algorithm = fields.Function(
        lambda obj: create_one_to_many_link(
            obj, link_to="algorithm", link_from="user_id"
        )
    )
    server = fields.Nested("Vantage6ServerOutputSchema", exclude=["users"])


class ReviewOutputSchema(HATEOASModelSchema):
    class Meta:
        model = Review

    reviewer = fields.Nested("UserOutputSchema")
    algorithm_id = fields.Integer(data_key="algorithm_id")
