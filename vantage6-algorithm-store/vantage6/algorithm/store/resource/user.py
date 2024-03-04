# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus

import sqlalchemy
from flask import request, g
from flask_restful import Api

from vantage6.algorithm.store.model import Vantage6Server
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.resource import with_permission, AlgorithmStoreResources
from vantage6.common import logger_name
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.algorithm.store import db
from vantage6.algorithm.store.permission import Operation as P, PermissionManager
from vantage6.algorithm.store.model.user import User as db_User

from vantage6.algorithm.store.resource.schema.input_schema import UserInputSchema
from vantage6.algorithm.store.resource.schema.output_schema import UserOutputSchema

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the user resource.

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
        Users,
        path,
        endpoint="user_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        User,
        path + "/<int:id>",
        endpoint="user_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """

    log.debug("Loading module users permission")
    add = permissions.appender(module_name)
    add(P.VIEW, description="View any user")
    add(P.CREATE, description="Create a new user")
    add(P.EDIT, description="Edit any user")
    add(P.DELETE, description="Delete any user")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
user_output_schema = UserOutputSchema()
user_input_schema = UserInputSchema()


# user_schema_with_permissions = UserWithPermissionDetailsSchema()


class Users(AlgorithmStoreResources):
    @with_permission(module_name, Operation.VIEW)
    def get(self):
        """List users
        ---
        description: >-
            Returns a list of users that you are allowed to see.

        parameters:
          - in: query
            name: username
            schema:
              type: string
            description: >-
              Name to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character

          - in: query
            name: role_id
            schema:
              type: integer
            description: Role that is assigned to user
            description: Number of items per page (default=10)
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

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Invalid values provided for request parameters

        security:
            - bearerAuth: []

        tags: ["User"]
        """
        args = request.args
        q = g.session.query(db_User)

        # filter by any field of this endpoint
        for param in ["username"]:
            if param in args:
                q = q.filter(getattr(db.User, param).like(args[param]))

        # find users with a particular role
        if "role_id" in args:
            role = db.Role.get(args["role_id"])
            if not role:
                return {
                    "msg": f'Role with id={args["role_id"]} does not exist!'
                }, HTTPStatus.BAD_REQUEST

            q = (
                q.join(db.Permission)
                .join(db.Role)
                .filter(db.Role.id == args["role_id"])
            )

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.User)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        # model serialization
        return self.response(page, user_output_schema)

    @with_permission(module_name, Operation.CREATE)
    def post(self):
        """Create user
        ---
        description: >-
          Creates new user from the request data.\n

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  username:
                    type: string
                    description: Unique username
                  roles:
                    type: array
                    items:
                      type: integer
                    description: User's roles

        responses:
          201:
            description: Ok
          400:
            description: User already exists
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["User"]
        """
        data = request.get_json()
        # the assumption is that it is possible to create only users linked to your own server
        server = Vantage6Server.get_by_url(request.headers["Server-Url"])
        # validate request body
        errors = user_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # check unique constraints
        if db.User.get_by_server(username=data["username"], v6_server_id=server.id):
            return {"msg": "User already registered."}, HTTPStatus.BAD_REQUEST

        # process the required roles. It is only possible to assign roles with
        # rules that you already have permission to. This way we ensure you can
        # never extend your power on your own.
        potential_roles = data.get("roles")
        roles = []
        if potential_roles:
            for role in potential_roles:
                role_ = db.Role.get(role)
                if role_:
                    denied = self.permissions.check_user_rules(role_.rules)
                    if denied:
                        return denied, HTTPStatus.UNAUTHORIZED
                    roles.append(role_)

        user = db.User(
            username=data["username"],
            v6_server_id=server.id,
            roles=roles,
        )

        user.save()

        return user_output_schema.dump(user), HTTPStatus.CREATED


class User(AlgorithmStoreResources):
    @with_permission(module_name, Operation.VIEW)
    def get(self, id):
        """Get user
        ---
        description: >-
            Returns the user specified by the id.\n


        parameters:
            - in: path
              name: id
              schema:
                type: integer
              description: User id
              required: true

        responses:
            200:
                description: Ok
            404:
                description: User not found
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["User"]
        """
        user = db.User.get(id)
        if not user:
            return {"msg": f"user id={id} is not found"}, HTTPStatus.NOT_FOUND

        return user_output_schema.dump(user, many=False), HTTPStatus.OK

    @with_permission(module_name, Operation.EDIT)
    def patch(self, id):
        """Update user
        ---
        description: >-
          Update user information.\n


        requestBody:
          content:
            application/json:
              schema:
                properties:
                  roles:
                    type: array
                    items:
                      type: integer
                    description: User's roles

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: User id
            required: true

        responses:
          200:
            description: Ok
          400:
            description: User cannot be updated to contents of request body,
              e.g. due to duplicate email address.
          404:
            description: User not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["User"]
        """
        user = db.User.get(id)
        if not user:
            return {"msg": f"user id={id} not found"}, HTTPStatus.NOT_FOUND

        data = request.get_json()
        # validate request body
        errors = user_input_schema.validate(data, partial=True)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # request parser is awefull with lists
        if "roles" in data:
            # validate that these roles exist
            roles = []
            for role_id in data["roles"]:
                role = db.Role.get(role_id)
                if not role:
                    return {
                        "msg": f"Role={role_id} can not be found!"
                    }, HTTPStatus.NOT_FOUND
                roles.append(role)

            # validate that user is not changing their own roles

            if user == g.user:
                return {
                    "msg": "You can't changes your own roles!"
                }, HTTPStatus.UNAUTHORIZED

            # validate that user can assign these
            for role in roles:
                denied = self.permissions.check_user_rules(role.rules)
                if denied:
                    return denied, HTTPStatus.UNAUTHORIZED

            # validate that user is not deleting roles they cannot assign
            deleted_roles = [r for r in user.roles if r not in roles]
            for role in deleted_roles:
                denied = self.permissions.check_user_rules(role.rules)
                if denied:
                    return {
                        "msg": (
                            f"You are trying to delete the role {role.name} from "
                            "this user but that is not allowed because they have "
                            f"permissions you don't have: {denied['msg']} (and "
                            "they do!)"
                        )
                    }, HTTPStatus.UNAUTHORIZED

            user.roles = roles

        try:
            user.save()
        except sqlalchemy.exc.IntegrityError as e:
            log.error(e)
            user.session.rollback()
            return {
                "msg": "User could not be updated with those parameters."
            }, HTTPStatus.BAD_REQUEST

        return user_output_schema.dump(user), HTTPStatus.OK

    @with_permission(module_name, Operation.DELETE)
    def delete(self, id):
        """Remove user.
        ---
        description: >-
          Unregister the vantage6 user account from the algorithm store.\n

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: User id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: User not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["User"]
        """
        user = db.User.get(id)
        if not user:
            return {"msg": f"user id={id} not found"}, HTTPStatus.NOT_FOUND

        user.delete()
        log.info(f"user id={id} is removed from the database")
        return {"msg": f"user id={id} is removed from the database"}, HTTPStatus.OK
