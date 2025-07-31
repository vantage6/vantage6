# -*- coding: utf-8 -*-
import logging
from http import HTTPStatus

from flask.globals import request
from flask_restful import Api
from sqlalchemy import select

from vantage6.common import logger_name

from vantage6.backend.common.resource.error_handling import handle_exceptions
from vantage6.backend.common.resource.input_schema import RoleInputSchema
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.backend.common.resource.role import (
    apply_user_filter,
    can_delete_dependents,
    check_default_role,
    filter_by_attribute,
    get_role,
    get_rules,
    update_role,
    validate_request_body,
    validate_user_exists,
)

from vantage6.algorithm.store import db
from vantage6.algorithm.store.default_roles import DefaultRole
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.permission import PermissionManager
from vantage6.algorithm.store.resource import AlgorithmStoreResources, with_permission
from vantage6.algorithm.store.resource.schema.output_schema import (
    RoleOutputSchema,
    RuleOutputSchema,
)

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
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Role,
        path + "/<int:role_id>",
        endpoint="role_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )


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
    add(operation=Operation.VIEW, description="View a role")
    add(operation=Operation.EDIT, description="Edit a role")
    add(operation=Operation.DELETE, description="Delete a role")


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
role_output_schema = RoleOutputSchema()
rule_schema = RuleOutputSchema()
role_input_schema = RoleInputSchema(default_roles=DefaultRole.list())


class Roles(AlgorithmStoreResources):
    @with_permission(module_name, Operation.VIEW)
    @handle_exceptions
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
        query = select(db.Role)

        args = request.args

        query = filter_by_attribute(db, ["name", "description"], query, args)

        if "user_id" in args:
            validate_user_exists(db, args["user_id"])
            query = apply_user_filter(db, query, args["user_id"])

        page = Pagination.from_query(query, request, db.Role)

        return self.response(page, role_output_schema)

    @with_permission(module_name, Operation.CREATE)
    @handle_exceptions
    def post(self):
        """Creates a new role.
        ---
        description: >-
          Create a new role. You can only assign rules that you own. You need
          permission to create roles.\n

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for role
                  description:
                    type: string
                    description: Human readable description of the role
                  rules:
                    type: array
                    items:
                      type: integer
                      description: Rule id's to assign to role

        responses:
          201:
            description: Created
          400:
            description: Non-allowed role name
          401:
            description: Unauthorized
          404:
            description: Rule was not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        data = request.get_json()
        validate_request_body(role_input_schema, data)
        rules = get_rules(data, db)
        self.permissions.check_user_rules(rules)
        role = db.Role(
            name=data.get("name"), description=data.get("description"), rules=rules
        )
        role.save()

        return role_output_schema.dump(role, many=False), HTTPStatus.CREATED


class Role(AlgorithmStoreResources):
    """Role/:id resource"""

    @with_permission(module_name, Operation.VIEW)
    @handle_exceptions
    def get(self, role_id: int):
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
        role = get_role(db, role_id)
        return role_output_schema.dump(role, many=False), HTTPStatus.OK

    @with_permission(module_name, Operation.EDIT)
    @handle_exceptions
    def patch(self, role_id: int):
        """Updates a role
        ---
        description: >-
          Update a role. You can only assign rules that you own. You need
          permission to edit roles.\n

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            required: true
            description: Role id

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for role
                  description:
                    type: string
                    description: Human readable description of the role
                  rules:
                    type: array
                    items:
                      type: integer
                      description: Rule id's to assign to role

        responses:
          200:
            description: Ok
          400:
            description: Non-allowed role name
          401:
            description: Unauthorized
          404:
            description: Rule was not found

        security:
          - bearerAuth: []

        tags: ["Role"]
        """
        data = request.get_json()
        validate_request_body(role_input_schema, data, partial=True)
        role = get_role(db, role_id)
        check_default_role(role, DefaultRole.list())
        role = update_role(role, data, db, self.permissions)
        role.save()
        return role_output_schema.dump(role, many=False), HTTPStatus.OK

    @with_permission(module_name, Operation.DELETE)
    @handle_exceptions
    def delete(self, role_id: int):
        """Deletes a role
        ---

        description: >-
            Deletes a role.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              required: true
              description: Role id

        responses:
          204:
            description: No content
          401:
            description: Unauthorized
          404:
            description: Role not found

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        role = get_role(db, role_id)
        check_default_role(role, DefaultRole.list())
        can_delete_dependents(role, request.args.get("delete_dependents", False))
        role.delete()
        return {"msg": "Role removed from the database."}, HTTPStatus.OK
