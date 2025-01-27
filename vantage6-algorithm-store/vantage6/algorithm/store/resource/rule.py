import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import Api
from sqlalchemy import and_, select

from vantage6.common import logger_name
from vantage6.algorithm.store import db
from vantage6.algorithm.store.resource import (
    AlgorithmStoreResources,
    with_authentication,
)
from vantage6.algorithm.store.resource.schema.output_schema import RuleOutputSchema
from vantage6.backend.common.resource.pagination import Pagination


module_name = logger_name(__name__)
log = logging.getLogger(module_name)
rule_schema = RuleOutputSchema()


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
    # api.add_resource(
    #     Rule,
    #     path + "/<int:id>",
    #     endpoint="rule_with_id",
    #     methods=("GET",),
    #     resource_class_kwargs=services,
    # )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Rules(AlgorithmStoreResources):
    @with_authentication()
    def get(self):
        """List algorithm store rules
        ---
        description: >-
            List of all available rules at the algorithm store. The user must be
            authenticated, but does not require any additional permissions to
            view the rules.

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
              name: role_id
              schema:
                type: integer
              description: Get rules for a specific role
            - in: query
              name: username
              schema:
                type: string
              description: Get rules for a specific user. Should be used in combination
                with server_url, as you need both to identify a user.
            - in: query
              name: server_url
              schema:
                type: string
              description: Get rules for a specific user - server combination. Should be
                used in combination with username, as you need both to identify a user.
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
        for param in ["name", "operation"]:
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

        # filters to get rules of a specific user
        username = args.get("username")
        server_url = args.get("server_url")
        if (username and not server_url) or (server_url and not username):
            return {
                "msg": "Both username and server_url are required to filter by user!"
            }, HTTPStatus.BAD_REQUEST
        elif username and server_url:
            server = db.Vantage6Server.get_by_url(server_url)
            if not server:
                return {
                    "msg": f'Server with url="{server_url}" is not whitelisted at this'
                    "algorithm store!"
                }, HTTPStatus.BAD_REQUEST
            user = db.User.get_by_server(username, server.id)
            if not user:
                return {
                    "msg": f'User with username="{username}" from server with url='
                    f'"{server_url}" is not registered at this algorithm store!'
                }, HTTPStatus.BAD_REQUEST
            # TODO when algorithm store gets option to assign loose rules to users,
            # uncomment and modify the lines in the query below
            q = (
                q.join(db.role_rule_association)
                .join(db.Role)
                .join(db.Permission)
                .join(db.User)
                # .outerjoin(db.UserPermission, db.Rule.id == db.UserPermission.c.rule_id)
                .filter(
                    # or_(
                    and_(
                        db.User.username == username,
                        db.User.v6_server_id == server.id,
                    ),
                    # db.UserPermission.c.user_id == user.id,
                    # )
                )
            )

        # check if pagination is disabled
        paginate = True
        if "no_pagination" in args and args["no_pagination"] == "1":
            paginate = False

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Rule, paginate=paginate)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        # model serialization
        return self.response(page, rule_schema)


# class Rule(ServicesResources):
#     @with_user
#     def get(self, id):
#         """Returns a specific rule
#         ---
#         description: >-
#             Get a rule by it's id. The user must be authenticated, but does
#             not require any additional permissions to view rules.\n

#             Accesible to users.

#         parameters:
#         - in: path
#           name: id
#           schema:
#               type: integer
#           minimum: 1
#           description: rule_id
#           required: true

#         responses:
#           200:
#             description: Ok
#           404:
#             description: Rule not found

#         security:
#             - bearerAuth: []

#         tags: ["Rule"]
#         """
#         rule = db.Rule.get(id)
#         if not rule:
#             return {"msg": f"Rule id={id} not found!"}, HTTPStatus.NOT_FOUND

#         return rule_schema.dump(rule, many=False), HTTPStatus.OK
