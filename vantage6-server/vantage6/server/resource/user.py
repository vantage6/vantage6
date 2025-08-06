import logging
from http import HTTPStatus

import sqlalchemy.exc
from flask import g, request
from flask_restful import Api
from keycloak import KeycloakAdmin, KeycloakDeleteError
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.common import logger_name

from vantage6.backend.common.auth import (
    KeycloakServiceAccount,
    create_service_account_in_keycloak,
    delete_service_account_in_keycloak,
    get_keycloak_admin_client,
    get_keycloak_id_for_user,
)
from vantage6.backend.common.resource.error_handling import (
    BadRequestError,
    UnauthorizedError,
    handle_exceptions,
)
from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
    Scope as S,
)
from vantage6.server.resource import (
    ServicesResources,
    get_org_ids_from_collabs,
    with_user,
)
from vantage6.server.resource.common.input_schema import (
    UserDeleteInputSchema,
    UserEditInputSchema,
    UserInputSchema,
)
from vantage6.server.resource.common.output_schema import (
    UserSchema,
    UserWithPermissionDetailsSchema,
)

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
        CurrentUser,
        path + "/me",
        endpoint="user_me",
        methods=("GET",),
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
    add = permissions.appender(module_name)
    add(S.GLOBAL, P.VIEW, description="View any user")
    add(S.COLLABORATION, P.VIEW, description="View users from your collaboration")
    add(S.ORGANIZATION, P.VIEW, description="View users from your organization")
    add(S.GLOBAL, P.CREATE, description="Create a new user for any organization")
    add(
        S.COLLABORATION,
        P.CREATE,
        description="Create a new user for organizations in your collaborations",
    )
    add(S.ORGANIZATION, P.CREATE, description="Create a new user for your organization")
    add(S.GLOBAL, P.EDIT, description="Edit any user")
    add(S.COLLABORATION, P.EDIT, description="Edit any user in your collaborations")
    add(S.ORGANIZATION, P.EDIT, description="Edit users from your organization")
    add(S.GLOBAL, P.DELETE, description="Delete any user")
    add(S.COLLABORATION, P.DELETE, description="Delete any user in your collaborations")
    add(S.ORGANIZATION, P.DELETE, description="Delete users from your organization")
    add(S.OWN, P.DELETE, description="Delete your own account")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
user_schema = UserSchema()
user_input_schema = UserInputSchema()
user_edit_input_schema = UserEditInputSchema()
user_schema_with_permissions = UserWithPermissionDetailsSchema()
user_delete_input_schema = UserDeleteInputSchema()


class UserBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)


class Users(UserBase):
    @with_user
    def get(self):
        """List users
        ---
        description: >-
            Returns a list of users that you are allowed to see.

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |User|Global|View|❌|❌|View any user details|\n
            |User|Collaboration|View|❌|❌|View user details from your
            collaborations|\n
            |User|Organization|View|❌|❌|View users from your organization|\n

            Accessible to users.

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
            name: organization_id
            schema:
              type: integer
            description: Organization id
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Collaboration id
          - in: query
            name: role_id
            schema:
              type: integer
            description: Role that is assigned to user
          - in: query
            name: rule_id
            schema:
              type: integer
            description: Rule that is assigned to user
          - in: query
            name: last_seen_from
            schema:
              type: date (yyyy-mm-dd)
            description: Show only users seen since this date
          - in: query
            name: last_seen_till
            schema:
              type: date (yyyy-mm-dd)
            description: Show only users last seen before this date
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
        q = select(db.User)

        # filter by any field of this endpoint
        if "username" in args:
            q = q.filter(db.User.username.like(args["username"]))
        if "organization_id" in args:
            if not self.r.allowed_for_org(P.VIEW, args["organization_id"]):
                return {
                    "msg": "You lack the permission view users from the "
                    f"organization with id {args['organization_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.User.organization_id == args["organization_id"])
        if "last_seen_till" in args:
            q = q.filter(db.User.last_seen <= args["last_seen_till"])
        if "last_seen_from" in args:
            q = q.filter(db.User.last_seen >= args["last_seen_from"])

        # find users with a particulare role or rule assigned
        if "role_id" in args:
            role = db.Role.get(args["role_id"])
            if not role:
                return {
                    "msg": f"Role with id={args['role_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            # note: We check if role has organization to ensure that users
            # with limited permissions can still see who have default roles
            elif (
                not self.r.allowed_for_org(P.VIEW, role.organization_id)
                and role.organization
            ):
                return {
                    "msg": "You lack the permission view users from the "
                    f"organization that role with id={role.organization_id} "
                    "belongs to!"
                }, HTTPStatus.UNAUTHORIZED
            q = (
                q.join(db.Permission)
                .join(db.Role)
                .filter(db.Role.id == args["role_id"])
            )

        if "rule_id" in args:
            rule = db.Rule.get(args["rule_id"])
            if not rule:
                return {
                    "msg": f"Rule with id={args['rule_id']} does not exist!"
                }, HTTPStatus.BAD_REQUEST
            q = (
                q.join(db.UserPermission)
                .join(db.Rule)
                .filter(db.Rule.id == args["rule_id"])
            )

        if "collaboration_id" in args:
            if not self.r.can_for_col(P.VIEW, args["collaboration_id"]):
                return {
                    "msg": "You lack the permission view all users from "
                    f"collaboration {args['collaboration_id']}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(
                db.User.organization_id.in_(
                    get_org_ids_from_collabs(g.user, args["collaboration_id"])
                )
            )

        # check permissions and apply filter if neccessary
        if not self.r.v_glo.can():
            if self.r.v_col.can():
                q = q.filter(
                    db.User.organization_id.in_(
                        [
                            org.id
                            for col in g.user.organization.collaborations
                            for org in col.organizations
                        ]
                        # include the organization of the user: in case the organization
                        # is not part of any collaboration they would otherwise not be
                        # visible
                        + [g.user.organization_id]
                    )
                )
            elif self.r.v_org.can():
                q = q.filter(db.User.organization_id == g.user.organization_id)
            elif "username" in args and args["username"] == g.user.username:
                # users can always see their own user
                pass
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.User)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # model serialization
        return self.response(page, user_schema)

    @with_user
    @handle_exceptions
    def post(self):
        """Create user
        ---
        description: >-
          Creates new user from the request data to the users organization.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |User|Global|Create|❌|❌|Create a new user|\n
          |User|Collaboration|Create|❌|❌|Create a new user for any
          organization in your collaborations|\n
          |User|Organization|Create|❌|❌|Create a new user as part of your
          organization|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  username:
                    type: string
                    description: Unique username
                  password:
                    type: string
                    description: Password
                  organization_id:
                    type: integer
                    description: Organization id to which user is assigned
                  roles:
                    type: array
                    items:
                      type: integer
                    description: User's roles
                  rules:
                    type: array
                    items:
                      type: integer
                    description: Extra rules for the user on top of the roles

        responses:
          201:
            description: Ok
          400:
            description: Username already exists or password is missing when
              the user has to be created in Keycloak
          401:
            description: Unauthorized
          404:
            description: Organization id does not exist

        security:
          - bearerAuth: []

        tags: ["User"]
        """
        data = request.get_json(silent=True)
        # validate request body
        try:
            data = user_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check unique constraints
        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists."}, HTTPStatus.BAD_REQUEST

        if (
            self.config.get("keycloak", {}).get("manage_users_and_nodes", True)
            and not data.get("password")
            and not data.get("is_service_account")
        ):
            raise ValidationError(
                "Password is required if the user has to be created in Keycloak"
            )
        elif data.get("is_service_account") and data.get("password"):
            raise ValidationError(
                "Password should not be provided if the user is a service account"
            )

        # check if the organization has been provided, if this is the case the
        # user needs global permissions in case it is not their own
        organization_id = g.user.organization_id
        if data.get("organization_id"):
            if data["organization_id"] != organization_id:
                if self.r.c_glo.can():
                    # check if organization exists
                    org = db.Organization.get(data["organization_id"])
                    if not org:
                        return {
                            "msg": "Organization does not exist."
                        }, HTTPStatus.NOT_FOUND
            organization_id = data["organization_id"]

        # check that user is allowed to create users
        if not self.r.allowed_for_org(P.CREATE, organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # process the required roles. It is only possible to assign roles with
        # rules that you already have permission to. This way we ensure you can
        # never extend your power on your own.
        potential_roles = data.get("roles")
        roles = []
        if potential_roles:
            for role in potential_roles:
                role_ = db.Role.get(role)
                if role_:
                    self.permissions.check_user_rules(role_.rules)
                    roles.append(role_)

                    # validate that the assigned role is either a general role
                    # or a role pertaining to that organization
                    if role_.organization and role_.organization.id != organization_id:
                        return {
                            "msg": (
                                "You can't assign that role as the role belongs to"
                                " a different organization than the user."
                            )
                        }, HTTPStatus.UNAUTHORIZED

        # You can only assign rules that you already have to others.
        potential_rules = data.get("rules")
        rules = []
        if potential_rules:
            rules = [db.Rule.get(rule) for rule in potential_rules if db.Rule.get(rule)]
            self.permissions.check_user_rules(rules)

        # Ok, looks like we got most of the security hazards out of the way. Create
        # the user in keycloak and database.
        keycloak_service_account: KeycloakServiceAccount | None = None
        if self.config.get("keycloak", {}).get("manage_users_and_nodes", True):
            if data.get("is_service_account"):
                keycloak_service_account = create_service_account_in_keycloak(
                    f"{data['username']}-user-client", is_node=False
                )
                keycloak_id = keycloak_service_account.user_id
            else:
                keycloak_id = self._create_user_in_keycloak(data)
        else:
            keycloak_id = get_keycloak_id_for_user(data["username"])

        user = db.User(
            username=data["username"],
            keycloak_id=keycloak_id,
            roles=roles,
            rules=rules,
            organization_id=organization_id,
            is_service_account=data.get("is_service_account", False),
            keycloak_client_id=(
                keycloak_service_account.client_id if keycloak_service_account else None
            ),
        )
        user.save()

        json_response = user_schema.dump(user)
        if keycloak_service_account:
            # share the client secret with the user so that they can login with it
            json_response["client_secret"] = keycloak_service_account.client_secret

        return json_response, HTTPStatus.CREATED

    def _create_user_in_keycloak(self, data):
        try:
            keycloak_admin: KeycloakAdmin = get_keycloak_admin_client()
            return keycloak_admin.create_user(
                {
                    "username": data["username"],
                    "enabled": True,
                    "credentials": [
                        {
                            "type": "password",
                            "value": data["password"],
                            "temporary": True,
                        }
                    ],
                }
            )
        except Exception as exc:
            log.exception(exc)
            raise BadRequestError("User could not be created in Keycloak") from exc


class CurrentUser(UserBase):
    @with_user
    def get(self):
        """Get your own user
        ---
        description: >-
          The user that is currently authenticated is returned. This is always
          allowed.

        parameters:
          - in: path
            name: include_permissions
            schema:
              type: boolean
            description: Whether or not to include extra permission info for
              the user. By default false.

        responses:
          200:
            description: Ok
        """
        schema = user_schema

        if request.args.get("include_permissions", False):
            schema = user_schema_with_permissions
        return schema.dump(g.user), HTTPStatus.OK


class User(UserBase):
    @with_user
    def get(self, id):
        """Get user
        ---
        description: >-
            Returns the user specified by the id.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |-- |--|--|--|--|--|\n
            |User|Global|View|❌|❌|View any user details|\n
            |User|Collaboration|View|❌|❌|View users from your
            collaborations|\n
            |User|Organization|View|❌|❌|View users from your
            organization|\n
            |User|Organization|Own|❌|❌|View details about your own user|\n

            Accessible to users.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              description: User id
              required: true
            - in: path
              name: include_permissions
              schema:
                type: boolean
              description: Whether or not to include extra permission info for
                the user. By default false.

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

        schema = user_schema

        if request.args.get("include_permissions", False):
            schema = user_schema_with_permissions

        # allow user to be returned if authenticated user can view users from
        # that organization or if the user is the same as the authenticated
        # user.
        same_user = g.user.id == user.id
        if same_user or self.r.allowed_for_org(P.VIEW, user.organization_id):
            return schema.dump(user, many=False), HTTPStatus.OK
        else:
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

    @with_user
    @handle_exceptions
    def patch(self, id):
        """Update user
        ---
        description: >-
          Update user information.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |User|Global|Edit|❌|❌|Edit any user|\n
          |User|Collaboration|Edit|❌|❌|Edit users in your collaborations|\n
          |User|Organization|Edit|❌|❌|Edit users in your organization|\n
          |User|Own|Edit|❌|❌|Edit your own user account|\n

          Accessible to users.

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
                  rules:
                    type: array
                    items:
                      type: integer
                    description: Extra rules for the user on top of the roles

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
          500:
            description: Error updating user in database
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
        if data.get("password"):
            return {
                "msg": "You cannot change your password here!"
            }, HTTPStatus.BAD_REQUEST
        try:
            data = user_edit_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check permissions
        if not self.r.allowed_for_org(P.EDIT, user.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # request parser is awful with lists
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
                self.permissions.check_user_rules(role.rules)

                # validate that the assigned role is either a general role or a
                # role pertaining to that organization
                if role.organization and role.organization.id != user.organization_id:
                    return {
                        "msg": (
                            "You can't assign that role to that user as the role "
                            "belongs to a different organization than the user "
                        )
                    }, HTTPStatus.UNAUTHORIZED

            # validate that user is not deleting roles they cannot assign
            # e.g. an organization admin is not allowed to delete a root role
            deleted_roles = [r for r in user.roles if r not in roles]
            for role in deleted_roles:
                self.permissions.check_user_rules(role.rules)
            user.roles = roles

        if "rules" in data:
            # validate that these rules exist
            rules = []
            for rule_id in data["rules"]:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {
                        "msg": f"Rule={rule_id} can not be found!"
                    }, HTTPStatus.NOT_FOUND
                rules.append(rule)

            # validate that user is not changing their own rules
            if user == g.user:
                return {
                    "msg": "You can't changes your own rules!"
                }, HTTPStatus.UNAUTHORIZED

            # validate that user can assign these
            self.permissions.check_user_rules(rules)

            # validate that user is not deleting rules they do not have
            # themselves
            deleted_rules = [r for r in user.rules if r not in rules]
            try:
                self.permissions.check_user_rules(deleted_rules)
            except UnauthorizedError as e:
                return {
                    "msg": "You cannot delete rules you do not have! " + str(e)
                }, HTTPStatus.UNAUTHORIZED

            user.rules = rules

        try:
            user.save()
        except sqlalchemy.exc.IntegrityError as e:
            log.error(e)
            user.session.rollback()
            return {
                "msg": "User could not be updated with those parameters."
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        return user_schema.dump(user), HTTPStatus.OK

    @with_user
    @handle_exceptions
    def delete(self, id):
        """Remove user.
        ---
        description: >-
          Delete a user account permanently.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |User|Global|Delete|❌|❌|Delete any user|\n
          |User|Collaboration|Delete|❌|❌|Delete users from your
          collaboration|\n
          |User|Organization|Delete|❌|❌|Delete users from your
          organization|\n
          |User|Own|Delete|❌|❌|Delete your own account|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: User id
            required: true
          - in: query
            name: delete_dependents
            schema:
              type: boolean
            description: If set to true, the user will be deleted along with
              all tasks they created (default=False)

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
        params = request.args
        try:
            params = user_delete_input_schema.load(params)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        user = db.User.get(id)
        if not user:
            return {"msg": f"user id={id} not found"}, HTTPStatus.NOT_FOUND

        if not (self.r.d_own.can() and user == g.user) and not self.r.allowed_for_org(
            P.DELETE, user.organization_id
        ):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # check if user created any tasks
        if user.created_tasks:
            if not params.get("delete_dependents", False):
                return {
                    "msg": f"User has created {len(user.created_tasks)} tasks."
                    " Please delete those first, or set the "
                    "`delete_dependents` parameter to true to delete them "
                    "automatically together with this user."
                }, HTTPStatus.BAD_REQUEST
            else:
                log.warning(
                    "Deleting %s tasks created by user id=%s",
                    len(user.created_tasks),
                    id,
                )
                for task in user.created_tasks:
                    task.delete()

        if self.config.get("keycloak", {}).get("manage_users_and_nodes", True):
            if user.is_service_account:
                delete_service_account_in_keycloak(user.keycloak_client_id)
            else:
                self._delete_user_in_keycloak(user)
        else:
            log.info("User id=%s will not be deleted from Keycloak", id)

        user.delete()
        log.info("user id=%s is removed from the database", id)
        return {"msg": f"user id={id} is removed from the database"}, HTTPStatus.OK

    def _delete_user_in_keycloak(self, user):
        keycloak_admin = get_keycloak_admin_client()
        try:
            keycloak_admin.delete_user(user.keycloak_id)
        except KeycloakDeleteError as exc:
            log.exception(exc)
            raise BadRequestError("User could not be deleted from Keycloak") from exc
