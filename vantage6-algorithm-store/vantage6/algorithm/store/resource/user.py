# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from flask import request, g
from flask_restful import Api
from marshmallow import ValidationError

from vantage6.common import logger_name
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.algorithm.store import db
from vantage6.algorithm.store.permission import Operation as P, PermissionManager
from vantage6.algorithm.store.model.user import User as db_User
from vantage6.algorithm.store.model import Vantage6Server
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.resource import (
    request_from_store_to_v6_server,
    with_permission,
    AlgorithmStoreResources,
)

from vantage6.algorithm.store.resource.schema.input_schema import (
    UserInputSchema,
    UserUpdateInputSchema,
)
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
user_patch_input_schema = UserUpdateInputSchema()


# user_schema_with_permissions = UserWithPermissionDetailsSchema()


class Users(AlgorithmStoreResources):
    @with_permission(module_name, Operation.VIEW)
    def get(self):
        """List users
        ---
        description: >-
            Returns a list of users registered in the algorithm store.

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
          - in: query
            name: can_review
            schema:
              type: boolean
            description: >-
              Filter users that can review algorithms. If true, only users that are
              allowed to review algorithms are returned. If false, only users that are
              not allowed to review algorithms are returned.
          - in: query
            name: reviewers_for_algorithm_id
            schema:
              type: integer
            description: >-
              Find users that can review the algorithm with the specified id. If the
              algorithm does not exist, an error is returned.
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
        q = select(db_User)

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

        # find users that can review algorithms
        # TODO v5+ this option is superseded by the reviewers_for_algorithm_id option.
        # Remove it in 5.0.
        if "can_review" in args:
            can_review = bool(args["can_review"])
            # TODO this approach may not be the most efficient if there are many users.
            # Consider improving.
            reviewers = [
                user.id for user in db.User.get() if user.can("review", Operation.EDIT)
            ]
            if can_review:
                q = q.filter(db.User.id.in_(reviewers))
            else:
                q = q.filter(db.User.id.notin_(reviewers))

        if "reviewers_for_algorithm_id" in args:
            try:
                algorithm_id = int(args["reviewers_for_algorithm_id"])
            except ValueError:
                return {
                    "msg": (
                        f"reviewers_for_algorithm_id must be an integer, but got: "
                        f"{args['reviewers_for_algorithm_id']}"
                    )
                }, HTTPStatus.BAD_REQUEST
            algorithm = db.Algorithm.get(algorithm_id)
            if not algorithm:
                return {
                    "msg": (
                        f"Algorithm with id={args['reviewers_for_algorithm_id']} does "
                        "not exist!"
                    )
                }, HTTPStatus.BAD_REQUEST

            # TODO this approach may not be the most efficient if there are many users.
            # Consider improving.
            reviewers = [
                user.id for user in db.User.get() if user.can("review", Operation.EDIT)
            ]
            # remove the user that is the developer of the algorithm, unless a dev
            # policy is set that allows this.
            can_review_self = self.config.get("dev", {}).get(
                "review_own_algorithm", False
            )
            if not can_review_self:
                reviewers = [r for r in reviewers if r != algorithm.developer.id]
            q = q.filter(db.User.id.in_(reviewers))

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
                    description: Username unique to the whitelisted server
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
        data = request.get_json(silent=True)
        # the assumption is that it is possible to create only users linked to your own server
        server = Vantage6Server.get_by_url(request.headers["Server-Url"])
        # validate request body
        try:
            data = user_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check unique constraints
        if db.User.get_by_server(username=data["username"], v6_server_id=server.id):
            return {"msg": "User already registered."}, HTTPStatus.BAD_REQUEST

        # check whether users of this server are allowed to get any permissions
        allowed_servers_to_edit = Policy.get_servers_with_edit_permission()
        if allowed_servers_to_edit and server.url not in allowed_servers_to_edit:
            return {
                "msg": f"Users from the server {server.url} are not allowed to be "
                "registered in this algorithm store by the store administrator."
            }, HTTPStatus.FORBIDDEN

        # Check if the user exists in the relevant vantage6 server. Note that this only
        # works if:
        # 1. the user executing this request is in the same v6 server
        # 2. They are allowed to see the user in the v6 server
        server_response, status_code = request_from_store_to_v6_server(
            url=f"{server.url}/user",
            params={"username": data["username"]},
        )
        if (
            status_code != HTTPStatus.OK
            or len(server_response.json().get("data", [])) != 1
        ):
            return {
                "msg": f"User '{data['username']}' not found in the Vantage6 server."
            }, HTTPStatus.BAD_REQUEST
        user_email = server_response.json()["data"][0].get("email")
        user_org = server_response.json()["data"][0]["organization"]["id"]

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
            email=user_email,
            organization_id=user_org,
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
                  email:
                    type: string
                    description: User's email address. Do not combine this option with
                      the update_email option.
                  update_email:
                    type: boolean
                    description: Whether to update the email address by using the value
                      from the vantage6 server. Do not combine this option with the
                      email option to manually set the email address.
                  organization_id:
                    type: integer
                    description: User's organization id. Can be written only if empty.

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

        data = request.get_json(silent=True)
        # validate request body
        try:
            data = user_patch_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        if email := data.get("email"):
            user.email = email
        elif "update_email" in data and data["update_email"]:
            server = Vantage6Server.get_by_url(request.headers["Server-Url"])
            server_response, status_code = request_from_store_to_v6_server(
                url=f"{server.url}/user",
                params={"username": user.username},
            )
            if (
                status_code != HTTPStatus.OK
                or len(server_response.json().get("data", [])) != 1
            ):
                return {
                    "msg": f"User '{user.username}' not found in the Vantage6 server."
                }, HTTPStatus.BAD_REQUEST
            user.email = server_response.json()["data"][0].get("email")
            if not user.email:
                log.warning(
                    "No email address found for user '%s' in the Vantage6 server.",
                    user.username,
                )
        if organization_id := data.get("organization_id") and not user.organization_id:
            user.organization_id = organization_id

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
        except IntegrityError as e:
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
        log.info("user id=%s is removed from the database", id)
        return {"msg": f"user id={id} is removed from the database"}, HTTPStatus.OK
