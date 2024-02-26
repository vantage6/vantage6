# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask import g, request
from flask_restful import Api

from vantage6.algorithm.store.model import Vantage6Server
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.resource import with_permission, AlgorithmStoreResources
from vantage6.common import logger_name
from vantage6.algorithm.store import db
from vantage6.algorithm.store.permission import (
    Operation as P,
    PermissionManager, RuleCollection
)
from vantage6.algorithm.store.model.user import User as db_User

from vantage6.algorithm.store.resource.schema.input_schema import UserInputSchema
from vantage6.algorithm.store.resource.schema.output_schema import (
    UserOutputSchema
)
from vantage6.backend.common.services_resources import BaseServicesResources

from vantage6.backend.common.resource.pagination import Pagination

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

    pass
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Users,
        path,
        endpoint='user_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    # api.add_resource(
    #     User,
    #     path + '/<int:id>',
    #     endpoint='user_with_id',
    #     methods=('GET', 'PATCH', 'DELETE'),
    #     resource_class_kwargs=services
    # )


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

    log.debug(f"Loading module users permission")
    add = permissions.appender(module_name)
    add(P.VIEW,
        description='View any user')
    add(P.CREATE,
        description='Create a new user')
    add(P.EDIT,
        description='Edit any user')
    add(P.DELETE, description='Delete any user')


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
        for param in ['username', 'id_server']:
            if param in args:
                q = q.filter(getattr(db.User, param).like(args[param]))

        # find users with a particular role
        if 'role_id' in args:
            role = db.Role.get(args['role_id'])
            if not role:
                return {
                    'msg': f'Role with id={args["role_id"]} does not exist!'
                }, HTTPStatus.BAD_REQUEST

            q = q.join(db.Permission).join(db.Role) \
                .filter(db.Role.id == args['role_id'])

        # TODO: add pagination
        return user_output_schema.dump(q.all(), many=True), HTTPStatus.OK

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
                  id_server:
                    type: integer
                    description: ID of the user in the v6 server

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
        server = Vantage6Server.get_by_url(request.headers['Server-Url'])
        # validate request body
        errors = user_input_schema.validate(data)
        if errors:
            return {'msg': 'Request body is incorrect', 'errors': errors}, \
                HTTPStatus.BAD_REQUEST

        # check unique constraints
        if db.User.get_by_server(id_server=data["id_server"], v6_server_id=server.id):
            return {"msg": "User already registered."}, HTTPStatus.BAD_REQUEST

        if db.User.username_exists(data["username"]):
            return {"msg": f"Username already exists."}, HTTPStatus.BAD_REQUEST

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
            id_server=data["id_server"],
            username=data["username"],
            v6_server_id=server.id,
            roles=roles
        )

        user.save()

        return user_output_schema.dump(user), HTTPStatus.CREATED

# class User(UserBase):
#
#     @with_user
#     def get(self, id):
#         """Get user
#         ---
#         description: >-
#             Returns the user specified by the id.\n
#
#             ### Permission Table\n
#             |Rule name|Scope|Operation|Assigned to node|Assigned to container|
#             Description|\n
#             |-- |--|--|--|--|--|\n
#             |User|Global|View|❌|❌|View any user details|\n
#             |User|Collaboration|View|❌|❌|View users from your
#             collaborations|\n
#             |User|Organization|View|❌|❌|View users from your
#             organization|\n
#             |User|Organization|Own|❌|❌|View details about your own user|\n
#
#             Accessible to users.
#
#         parameters:
#             - in: path
#               name: id
#               schema:
#                 type: integer
#               description: User id
#               required: true
#             - in: path
#               name: include_permissions
#               schema:
#                 type: boolean
#               description: Whether or not to include extra permission info for
#                 the user. By default false.
#
#         responses:
#             200:
#                 description: Ok
#             404:
#                 description: User not found
#             401:
#                 description: Unauthorized
#
#         security:
#             - bearerAuth: []
#
#         tags: ["User"]
#         """
#         user = db.User.get(id)
#         if not user:
#             return {"msg": f"user id={id} is not found"}, HTTPStatus.NOT_FOUND
#
#         schema = user_schema
#
#         if request.args.get('include_permissions', False):
#             schema = user_schema_with_permissions
#
#         # allow user to be returned if authenticated user can view users from
#         # that organization or if the user is the same as the authenticated
#         # user.
#         same_user = g.user.id == user.id
#         if (same_user or self.r.can_for_org(P.VIEW, user.organization_id)):
#             return schema.dump(user, many=False), HTTPStatus.OK
#         else:
#             return {'msg': 'You lack the permission to do that!'}, \
#                     HTTPStatus.UNAUTHORIZED
#
#     @with_user
#     def patch(self, id):
#         """Update user
#         ---
#         description: >-
#           Update user information.\n
#
#           ### Permission Table\n
#           |Rule name|Scope|Operation|Assigned to node|Assigned to container|
#           Description|\n
#           |--|--|--|--|--|--|\n
#           |User|Global|Edit|❌|❌|Edit any user|\n
#           |User|Collaboration|Edit|❌|❌|Edit users in your collaborations|\n
#           |User|Organization|Edit|❌|❌|Edit users in your organization|\n
#           |User|Own|Edit|❌|❌|Edit your own user account|\n
#
#           Accessible to users.
#
#         requestBody:
#           content:
#             application/json:
#               schema:
#                 properties:
#                   username:
#                     type: string
#                     description: Unique username
#                   firstname:
#                     type: string
#                     description: First name
#                   lastname:
#                     type: string
#                     description: Last name
#                   email:
#                     type: string
#                     description: Email address
#                   roles:
#                     type: array
#                     items:
#                       type: integer
#                     description: User's roles
#                   rules:
#                     type: array
#                     items:
#                       type: integer
#                     description: Extra rules for the user on top of the roles
#
#         parameters:
#           - in: path
#             name: id
#             schema:
#               type: integer
#             description: User id
#             required: true
#
#         responses:
#           200:
#             description: Ok
#           400:
#             description: User cannot be updated to contents of request body,
#               e.g. due to duplicate email address.
#           404:
#             description: User not found
#           401:
#             description: Unauthorized
#
#         security:
#           - bearerAuth: []
#
#         tags: ["User"]
#         """
#         user = db.User.get(id)
#         if not user:
#             return {"msg": f"user id={id} not found"}, \
#                 HTTPStatus.NOT_FOUND
#
#         data = request.get_json()
#         # validate request body
#         errors = user_input_schema.validate(data, partial=True)
#         if errors:
#             return {'msg': 'Request body is incorrect', 'errors': errors}, \
#                 HTTPStatus.BAD_REQUEST
#         if data.get("password"):
#             return {"msg": "You cannot change your password here!"}, \
#                 HTTPStatus.BAD_REQUEST
#
#         # check permissions
#         if not (self.r.e_own.can() and user == g.user) and \
#                 not self.r.can_for_org(P.EDIT, user.organization_id):
#             return {'msg': 'You lack the permission to do that!'}, \
#                 HTTPStatus.UNAUTHORIZED
#
#         # update user and check for unique constraints
#         if data.get("username") is not None:
#             if user.username != data["username"]:
#                 if db.User.exists("username", data["username"]):
#                     return {
#                         "msg": "User with that username already exists"
#                     }, HTTPStatus.BAD_REQUEST
#                 elif user.id != g.user.id:
#                     return {
#                         "msg": "You cannot change the username of another user"
#                     }, HTTPStatus.BAD_REQUEST
#             user.username = data["username"]
#         if data.get("firstname") is not None:
#             user.firstname = data["firstname"]
#         if data.get("lastname") is not None:
#             user.lastname = data["lastname"]
#         if data.get("email") is not None:
#             if (user.email != data["email"] and
#                     db.User.exists("email", data["email"])):
#                 return {
#                     "msg": "User with that email already exists."
#                 }, HTTPStatus.BAD_REQUEST
#             user.email = data["email"]
#
#         # request parser is awefull with lists
#         if 'roles' in data:
#             # validate that these roles exist
#             roles = []
#             for role_id in data['roles']:
#                 role = db.Role.get(role_id)
#                 if not role:
#                     return {'msg': f'Role={role_id} can not be found!'}, \
#                         HTTPStatus.NOT_FOUND
#                 roles.append(role)
#
#             # validate that user is not changing their own roles
#             if user == g.user:
#                 return {'msg': "You can't changes your own roles!"}, \
#                     HTTPStatus.UNAUTHORIZED
#
#             # validate that user can assign these
#             for role in roles:
#                 denied = self.permissions.check_user_rules(role.rules)
#                 if denied:
#                     return denied, HTTPStatus.UNAUTHORIZED
#
#                 # validate that the assigned role is either a general role or a
#                 # role pertaining to that organization
#                 if (role.organization and
#                         role.organization.id != user.organization_id):
#                     return {'msg': (
#                         "You can't assign that role to that user as the role "
#                         "belongs to a different organization than the user "
#                     )}, HTTPStatus.UNAUTHORIZED
#
#             # validate that user is not deleting roles they cannot assign
#             # e.g. an organization admin is not allowed to delete a root role
#             deleted_roles = [r for r in user.roles if r not in roles]
#             for role in deleted_roles:
#                 denied = self.permissions.check_user_rules(role.rules)
#                 if denied:
#                     return {"msg": (
#                         f"You are trying to delete the role {role.name} from "
#                         "this user but that is not allowed because they have "
#                         f"permissions you don't have: {denied['msg']} (and "
#                         "they do!)"
#                     )}, HTTPStatus.UNAUTHORIZED
#
#             user.roles = roles
#
#         if 'rules' in data:
#             # validate that these rules exist
#             rules = []
#             for rule_id in data['rules']:
#                 rule = db.Rule.get(rule_id)
#                 if not rule:
#                     return {'msg': f'Rule={rule_id} can not be found!'}, \
#                         HTTPStatus.NOT_FOUND
#                 rules.append(rule)
#
#             # validate that user is not changing their own rules
#             if user == g.user:
#                 return {'msg': "You can't changes your own rules!"}, \
#                     HTTPStatus.UNAUTHORIZED
#
#             # validate that user can assign these
#             denied = self.permissions.check_user_rules(rules)
#             if denied:
#                 return denied, HTTPStatus.UNAUTHORIZED
#
#             # validate that user is not deleting rules they do not have
#             # themselves
#             deleted_rules = [r for r in user.rules if r not in rules]
#             denied = self.permissions.check_user_rules(deleted_rules)
#             if denied:
#                 return {"msg": (
#                     f"{denied['msg']}. You can't delete permissions for "
#                     "another user that you don't have yourself!"
#                 )}, HTTPStatus.UNAUTHORIZED
#
#             user.rules = rules
#
#         try:
#             user.save()
#         except sqlalchemy.exc.IntegrityError as e:
#             log.error(e)
#             user.session.rollback()
#             return {
#                 "msg": "User could not be updated with those parameters."
#             }, HTTPStatus.BAD_REQUEST
#
#         return user_schema.dump(user), HTTPStatus.OK
#
#     @with_user
#     def delete(self, id):
#         """Remove user.
#         ---
#         description: >-
#           Delete a user account permanently.\n
#
#           ### Permission Table\n
#           |Rule name|Scope|Operation|Assigned to node|Assigned to container|
#           Description|\n
#           |--|--|--|--|--|--|\n
#           |User|Global|Delete|❌|❌|Delete any user|\n
#           |User|Collaboration|Delete|❌|❌|Delete users from your
#           collaboration|\n
#           |User|Organization|Delete|❌|❌|Delete users from your
#           organization|\n
#           |User|Own|Delete|❌|❌|Delete your own account|\n
#
#           Accessible to users.
#
#         parameters:
#           - in: path
#             name: id
#             schema:
#               type: integer
#             description: User id
#             required: true
#           - in: query
#             name: delete_dependents
#             schema:
#               type: boolean
#             description: If set to true, the user will be deleted along with
#               all tasks they created (default=False)
#
#         responses:
#           200:
#             description: Ok
#           404:
#             description: User not found
#           401:
#             description: Unauthorized
#
#         security:
#           - bearerAuth: []
#
#         tags: ["User"]
#         """
#         user = db.User.get(id)
#         if not user:
#             return {"msg": f"user id={id} not found"}, \
#                 HTTPStatus.NOT_FOUND
#
#         if not (self.r.d_own.can() and user == g.user) and \
#                 not self.r.can_for_org(P.DELETE, user.organization_id):
#             return {'msg': 'You lack the permission to do that!'}, \
#                 HTTPStatus.UNAUTHORIZED
#
#         # check if user created any tasks
#         if user.created_tasks:
#             params = request.args
#             if not params.get('delete_dependents', False):
#                 return {
#                     "msg": f"User has created {len(user.created_tasks)} tasks."
#                     " Please delete those first, or set the "
#                     "`delete_dependents` parameter to true to delete them "
#                     "automatically together with this user."
#                 }, HTTPStatus.BAD_REQUEST
#             else:
#                 log.warn(f"Deleting {len(user.created_tasks)} tasks created by"
#                          f" user id={id}")
#                 for task in user.created_tasks:
#                     task.delete()
#
#         user.delete()
#         log.info(f"user id={id} is removed from the database")
#         return {"msg": f"user id={id} is removed from the database"}, \
#             HTTPStatus.OK
