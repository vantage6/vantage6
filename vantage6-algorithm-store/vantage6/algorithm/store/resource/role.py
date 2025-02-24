# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import Api
from sqlalchemy import or_, select

from vantage6.algorithm.store.resource import with_permission
from vantage6.common import logger_name
from vantage6.algorithm.store.permission import PermissionManager
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.resource.schema.output_schema import RoleOutputSchema
from vantage6.algorithm.store import db
from vantage6.algorithm.store.resource import AlgorithmStoreResources
from vantage6.backend.common.resource.pagination import Pagination

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the role resource.

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
        Roles,
        path,
        endpoint="role_without_id",
        methods=("GET",),
        # methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Role,
        path + "/<int:id>",
        endpoint="role_with_id",
        methods=("GET",),
        # methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services,
    )
    # api.add_resource(
    #     RoleRules,
    #     path + '/<int:id>/rule/<int:rule_id>',
    #     endpoint='role_rule_with_id',
    #     methods=('DELETE', 'POST'),
    #     resource_class_kwargs=services
    # )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permissions.appender(module_name)
    add(operation=Operation.CREATE, description="Create role")
    add(operation=Operation.VIEW, description="View any role")
    add(operation=Operation.EDIT, description="Edit a role")
    add(operation=Operation.DELETE, description="Delete a role")


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
role_output_schema = RoleOutputSchema()
# rule_schema = RuleSchema()
# role_input_schema = RoleInputSchema()


class Roles(AlgorithmStoreResources):
    @with_permission(module_name, Operation.VIEW)
    def get(self):
        """Returns a list of roles
        ---

        description: >-
            Returns a list of roles.

        parameters:
            - in: query
              name: name
              schema:
                type: string
              description: >-
                Name to match with a LIKE operator. \n
                * The percent sign (%) represents zero, one, or multiple
                characters\n
                * underscore sign (_) represents one, single character
            - in: query
              name: description
              schema:
                type: string
              description: >-
                Description to match with a LIKE operator. \n
                * The percent sign (%) represents zero, one, or multiple
                characters\n
                * underscore sign (_) represents one, single character
            - in: query
              name: user_id
              schema:
                type: integer
              description: Get roles for this user id
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

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Improper values for pagination or sorting parameters

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        q = select(db.Role)

        args = request.args

        # filter by one or more names or descriptions
        for param in ["name", "description"]:
            filters = args.getlist(param)
            if filters:
                q = q.filter(or_(*[getattr(db.Role, param).like(f) for f in filters]))

        if "user_id" in args:
            user = db.User.get(args["user_id"])
            if not user:
                return {
                    "msg": f'User with id={args["user_id"]} does not ' "exist!"
                }, HTTPStatus.BAD_REQUEST

            q = (
                q.join(db.Permission)
                .join(db.User)
                .filter(db.User.id == args["user_id"])
            )

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Role)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        return self.response(page, role_output_schema)


class Role(AlgorithmStoreResources):
    """Role/:id resource"""

    @with_permission(module_name, Operation.VIEW)
    def get(self, id: int):
        """Returns a role
        ---

        description: >-
            Returns a role.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              required: true
              description: Role id

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          404:
            description: Role not found

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role id={id} not found"}, HTTPStatus.NOT_FOUND

        return role_output_schema.dump(role, many=False), HTTPStatus.OK
