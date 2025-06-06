import logging

from http import HTTPStatus
from flask import g
from flask.globals import request
from flask_restful import Api
from sqlalchemy import or_, select

from vantage6.server.resource import with_user, ServicesResources
from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.resource.common.output_schema import RuleSchema
from vantage6.backend.common.resource.pagination import Pagination


module_name = logger_name(__name__)
log = logging.getLogger(module_name)
rule_schema = RuleSchema()


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the rule resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Rules,
        path,
        endpoint="rule_without_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Rule,
        path + "/<int:id>",
        endpoint="rule_with_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Rules(ServicesResources):
    @with_user
    def get(self):
        """List Rules
        ---
        description: >-
            List of all available rules at the server. The user must be
            authenticated, but does not require any additional permissions to
            view the rules.\n

            Accesible to users.

        parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name of the rule
            - in: query
              name: operation
              schema:
                type: string
              description: Get rules for a specific type of operation
            - in: query
              name: scope
              schema:
                type: string
              description: Get rules for a specific scope
            - in: query
              name: role_id
              schema:
                type: integer
              description: Get rules for a specific role
            - in: query
              name: user_id
              schema:
                type: string
              description: Get rules for a specific user. This includes the
                rules that are part of the user's roles. If provided together with
                current_user, the current user will be used and user_id will be ignored.
            - in: query
              name: current_user
              schema:
                type: boolean
              description: Get rules for the current user
            - in: query
              name: page
              schema:
                type: integer
              description: Page number for pagination (default=1)
            - in: query
              name: per_page
              schema:
                type: integer
              description: Number of items per page (default=10)
            - in: query
              name: sort
              schema:
                type: string
              description: >-
                Sort by one or more fields, separated by a comma. Use a minus
                sign (-) in front of the field to sort in descending order.
            - in: query
              name: no_pagination
              schema:
                type: int
              description: >-
                If set to 1, pagination is disabled and all items are returned.

        responses:
          200:
            description: Ok
          400:
            description: Improper values for pagination or sorting parameters

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        q = select(db.Rule)

        args = request.args

        # filter by any field of this endpoint
        for param in ["name", "operation", "scope"]:
            if param in args:
                q = q.filter(getattr(db.Rule, param) == args[param])

        # find roles containing a specific rule
        if "role_id" in args:
            role = db.Role.get(args["role_id"])
            if not role:
                return {
                    "msg": f'Role with id={args["role_id"]} does not exist!'
                }, HTTPStatus.BAD_REQUEST
            q = (
                q.join(db.role_rule_association)
                .join(db.Role)
                .filter(db.Role.id == args["role_id"])
            )

        # find all rules of a specific user. This is done by first joining all
        # tables to find all rules originating from a user's roles. Then, we
        # do an outer join to find all rules that are directly assigned to the
        # user.
        if "user_id" in args or args.get("current_user", False):
            if args.get("current_user", False):
                user = g.user
            else:
                user = db.User.get(args["user_id"])
                if not user:
                    return {
                        "msg": f'User with id={args["user_id"]} does not exist!'
                    }, HTTPStatus.BAD_REQUEST

            # Create two subqueries - one for role-based permissions and one for direct
            # user permissions
            role_based_rules = (
                q.join(db.role_rule_association)
                .join(db.Role)
                .join(db.Permission)
                .join(db.User)
                .filter(db.User.id == user.id)
            )

            direct_user_rules = q.join(
                db.UserPermission, db.Rule.id == db.UserPermission.c.rule_id
            ).filter(db.UserPermission.c.user_id == user.id)

            # Combine both queries
            union_query = role_based_rules.union(direct_user_rules).subquery()
            q = select(db.Rule).join(union_query, db.Rule.id == union_query.c.id)

        # check if pagination is disabled
        paginate = True
        if "no_pagination" in args and args["no_pagination"] == "1":
            paginate = False

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Rule, paginate=paginate)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # model serialization
        return self.response(page, rule_schema)


class Rule(ServicesResources):
    @with_user
    def get(self, id):
        """Returns a specific rule
        ---
        description: >-
            Get a rule by it's id. The user must be authenticated, but does
            not require any additional permissions to view rules.\n

            Accesible to users.

        parameters:
        - in: path
          name: id
          schema:
              type: integer
          minimum: 1
          description: rule_id
          required: true

        responses:
          200:
            description: Ok
          404:
            description: Rule not found

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        rule = db.Rule.get(id)
        if not rule:
            return {"msg": f"Rule id={id} not found!"}, HTTPStatus.NOT_FOUND

        return rule_schema.dump(rule, many=False), HTTPStatus.OK
