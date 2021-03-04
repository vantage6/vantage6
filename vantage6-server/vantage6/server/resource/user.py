# -*- coding: utf-8 -*-
import logging
import sqlalchemy.exc

from http import HTTPStatus
from flask import g, request
from flask_restful import reqparse
from flasgger import swag_from
from pathlib import Path

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager
)
from vantage6.server.resource import (
    with_user,
    only_for,
    ServicesResources
)
from vantage6.server.resource._schema import UserSchema


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        User,
        path,
        endpoint='user_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        User,
        path + '/<int:id>',
        endpoint='user_with_id',
        methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    add = permissions.appender(module_name)
    add(S.GLOBAL, P.VIEW,
        description='View any user')
    add(S.ORGANIZATION, P.VIEW,
        description='View users from your organization')
    add(S.OWN, P.VIEW,
        description='View your own data')
    add(S.GLOBAL, P.CREATE,
        description='Create a new user for any organization')
    add(S.ORGANIZATION, P.CREATE,
        description='Create a new user for your organization')
    add(S.GLOBAL, P.EDIT,
        description='Edit any user')
    add(S.ORGANIZATION, P.EDIT,
        description='Edit users from your organization')
    add(S.OWN, P.EDIT,
        description='Edit your own info')
    add(S.GLOBAL, P.DELETE,
        description='Delete any user')
    add(S.ORGANIZATION, P.DELETE,
        description='Delete users from your organization')
    add(S.OWN, P.DELETE,
        description='Delete your own account')


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class User(ServicesResources):

    user_schema = UserSchema()

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/get_user_with_id.yaml")),
               endpoint='user_with_id')
    @swag_from(str(Path(r"swagger/get_user_without_id.yaml")),
               endpoint='user_without_id')
    def get(self, id=None):
        """Return user details."""
        many = not id
        user = db.User.get(id)
        if not user:
            return {"msg": f"user={id} is not found"}, HTTPStatus.NOT_FOUND

        # global scope can see all
        if self.r.v_glo.can():
            return self.user_schema.dump(user, many=many).data, \
                HTTPStatus.OK

        # organization scope can see their own organization users
        if self.r.v_org.can():
            if many:
                filtered_users = [user for user in user if user.organization
                                  == g.user.organization]
                return self.user_schema.dump(filtered_users, many=True).data, \
                    HTTPStatus.OK
            else:
                if user.organization != g.user.organization:
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED
                return self.user_schema.dump(user, many=False).data, \
                    HTTPStatus.OK

        # own scope can see their own user info
        if self.r.v_own.can():
            if not id:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            if user.id != g.user.id:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            return self.user_schema.dump(user, many=False).data, HTTPStatus.OK

        # if you get here... you do not have any permissions
        return {'msg': 'You lack the permission to do that!'}, \
            HTTPStatus.UNAUTHORIZED

    @with_user
    @swag_from(str(Path(r"swagger/post_user_without_id.yaml")),
               endpoint='user_without_id')
    def post(self):
        """Create a new User."""
        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=True)
        parser.add_argument("firstname", type=str, required=True)
        parser.add_argument("lastname", type=str, required=True)
        #TODO password should be send to the email, rather than setting it
        parser.add_argument("password", type=str, required=True)
        parser.add_argument("email", type=str, required=True)
        parser.add_argument("organization_id", type=int, required=False,
                            help="This is only used if you're root")
        parser.add_argument("roles", type=int, action="append", required=False)
        parser.add_argument("rules", type=int, action="append", required=False)
        data = parser.parse_args()

        # check unique constraints
        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists."}, HTTPStatus.BAD_REQUEST

        if db.User.exists("email", data["email"]):
            return {"msg": "email already exists."}, HTTPStatus.BAD_REQUEST

        # check if the organization has been profided, if this is the case the
        # user needs global permissions in case it is not their own
        organization_id = g.user.organization_id
        if data['organization_id']:
            if data['organization_id'] != organization_id and \
                    not self.r.c_glo.can():
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            organization_id = data['organization_id']

        # check that user is allowed to create users
        if not (self.r.c_glo.can() or self.r.c_org.can()):
            return {'msg': 'You lack the permission to do that!2'}, \
                HTTPStatus.UNAUTHORIZED

        # process the required roles. It is only possible to assign roles with
        # rules that you already have permission to. This way we ensure you can
        # never extend your power on your own.
        potential_roles = data.get("roles")
        roles = []
        if potential_roles:
            for role in potential_roles:
                role_ = db.Role.get(role)
                if role_:
                    denied = self.permissions.verify_user_rules(role_.rules)
                    if denied:
                        return denied, HTTPStatus.UNAUTHORIZED
                    roles.append(role_)

        # You can only assign rules that you already have to others.
        potential_rules = data["rules"]
        rules = []
        if potential_rules:
            rules = [db.Rule.get(rule) for rule in potential_rules
                     if db.Rule.get(rule)]
            denied = self.permissions.verify_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED

        # Ok, looks like we got most of the security hazards out of the way
        user = db.User(
            username=data["username"],
            firstname=data["firstname"],
            lastname=data["lastname"],
            roles=roles,
            rules=rules,
            organization_id=organization_id,
            email=data["email"],
            password=data["password"]
        )
        user.save()

        return self.user_schema.dump(user).data, HTTPStatus.CREATED

    @with_user
    @swag_from(str(Path(r"swagger/patch_user_with_id.yaml")),
               endpoint='user_with_id')
    def patch(self, id):

        user = db.User.get(id)

        if not user:
            return {"msg": f"user id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if not self.r.e_glo.can():
            if not (self.r.e_org.can() and user.organization ==
                    g.user.organization):
                if not (self.r.e_own.can() and user == g.user):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=False)
        parser.add_argument("firstname", type=str, required=False)
        parser.add_argument("lastname", type=str, required=False)
        # parser.add_argument("roles", type=int, action='append', required=False,
        #                     default=[], store_missing=False)
        # parser.add_argument("rules", type=int, action='append', required=False,
        #                     default=[], store_missing=False)
        parser.add_argument("password", type=str, required=False)
        parser.add_argument("email", type=str, required=False)
        parser.add_argument("organization_id", type=int, required=False)
        data = parser.parse_args()

        if data["firstname"]:
            user.firstname = data["firstname"]
        if data["lastname"]:
            user.lastname = data["lastname"]
        if data["password"]:
            user.password = data["password"]
        if data["email"]:
            user.email = data["email"]

        # request parser is awefull with lists
        json_data = request.get_json()
        if 'roles' in json_data:
            # validate that these roles exist
            roles = []
            for role_id in json_data['roles']:
                role = db.Role.get(role_id) # somehow a nontype endup here
                if not role:
                    return {'msg': f'Role={role_id} can not be found!'}, \
                        HTTPStatus.NOT_FOUND
                roles.append(role)

            # validate that user can assign these
            for role in roles:
                denied = self.permissions.verify_user_rules(role.rules)
                if denied:
                    return denied, HTTPStatus.UNAUTHORIZED

            user.roles = roles

        if 'rules' in json_data:
            # validate that these rules exist
            rules = []
            for rule_id in json_data['rules']:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {'msg': f'Rule={rule_id} can not be found!'}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)

            # validate that user can assign these
            denied = self.permissions.verify_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED

            user.rules = rules

        if data["organization_id"]:
            if not (self.r.e_glo.can() and data["organization_id"] !=
                    g.user.organization_id):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            else:
                log.warn(
                    f'Running as root and assigning (new) '
                    f'organization_id={data["organization_id"]}'
                )
                user.organization_id = data["organization_id"]

        try:
            user.save()
        except sqlalchemy.exc.IntegrityError as e:
            log.error(e)
            user.session.rollback()

        return self.user_schema.dump(user).data, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_user_with_id.yaml")),
               endpoint='user_with_id')
    def delete(self, id):
        """Remove user from the database."""
        user = db.User.get(id)
        if not user:
            return {"msg": f"user id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            if not (self.r.d_org.can() and user.organization ==
                    g.user.organization):
                if not (self.r.d_own.can() and user == g.user):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        user.delete()
        log.info(f"user id={id} is removed from the database")
        return {"msg": f"user id={id} is removed from the database"}, \
            HTTPStatus.OK
