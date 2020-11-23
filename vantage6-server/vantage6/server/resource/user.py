# -*- coding: utf-8 -*-
import logging
import sqlalchemy.exc

from http import HTTPStatus
from flask import g
from flask_restful import reqparse
from flasgger import swag_from
from pathlib import Path

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.permission import (
    register_rule,
    Scope,
    Operation
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
manage_users = register_rule(
    "manage users",
    [Scope.ORGANIZATION, Scope.GLOBAL],
    [Operation.EDIT, Operation.VIEW, Operation.DELETE, Operation.CREATE]
)


manage_roles = register_rule(
    "manage roles",
    [Scope.ORGANIZATION, Scope.GLOBAL],
    [Operation.EDIT, Operation.VIEW, Operation.DELETE, Operation.CREATE],
    "Assign roles to other users."
)


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class User(ServicesResources):

    user_schema = UserSchema()

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/get_user_with_id.yaml")),
               endpoint='user_with_id')
    @swag_from(str(Path(r"swagger/get_user_without_id.yaml")),
               endpoint='user_without_id')
    def get(self, id=None):
        """Return user details."""
        retval = db.User.get(id)
        is_root = g.user.username == "root"

        if id is None:
            # Only root can retrieve all users at once
            if is_root:
                return self.user_schema.dump(retval, many=True)

            # Everyone else can only list the users from their own organization
            else:
                org_id = g.user.organization_id
                filtered = [u for u in retval if u.organization_id == org_id]
                return self.user_schema.dump(filtered, many=True)

        if retval:
            # You either have to be root or someone from the same organization
            if is_root or (retval.organization_id == g.user.organization_id):
                return self.user_schema.dump(retval, many=False)

        return {"msg": f"user id {id} is not found"}, HTTPStatus.NOT_FOUND

    @with_user
    @swag_from(str(Path(r"swagger/post_user_without_id.yaml")),
               endpoint='user_without_id')
    def post(self):
        """Create a new User."""
        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=True)
        parser.add_argument("firstname", type=str, required=True)
        parser.add_argument("lastname", type=str, required=True)
        parser.add_argument("password", type=str, required=True)
        parser.add_argument("organization_id", type=int, required=False,
                            help="This is only used if you're root")
        parser.add_argument("roles", type=int, action="append", required=False)
        parser.add_argument("rules", type=int, action="append", required=False)
        parser.add_argument("email", type=str, required=True)
        data = parser.parse_args()

        # check unique constraints
        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists."}, HTTPStatus.BAD_REQUEST

        if db.User.exists("email", data["email"]):
            return {"msg": "email already exists."}, HTTPStatus.BAD_REQUEST

        # check if it is global or organization scope. Depending on that a
        # different permission is required.
        if 'organization_id' in data:
            manage_users(Scope.GLOBAL, Operation.CREATE).test(
                http_exception=HTTPStatus.FORBIDDEN
            )
            organization_id = data['organization_id']

        else:
            manage_users(Scope.ORGANIZATION, Operation.CREATE).test(
                http_exception=HTTPStatus.FORBIDDEN
            )
            organization_id = g.user.organization_id

        # process the required roles. It is only possible to assign roles with
        # rules that you already have permission to. This way we ensure you can
        # never extend your power on your own.
        potential_roles = data.get("roles")
        roles = []
        if potential_roles:
            for role in potential_roles:
                role_ = db.Role.get(role)
                if role_:
                    denied = self.verify_user_rules(role_.rules)
                    if denied:
                        return denied, HTTPStatus.UNAUTHORIZED
                    roles.append(role_)

        # You can only assign rules that you already have to others.
        potential_rules = data["rules"]
        rules = []
        if potential_rules:
            rules = [db.Rule.get(rule) for rule in potential_rules
                     if db.Rule.get(rule)]
            denied = self.verify_user_rules(rules)
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
            return {"msg": "user id={} not found".format(id)}, \
                HTTPStatus.NOT_FOUND

        is_root = g.user.username == 'root'
        if (user.organization_id != g.user.organization_id) and not is_root:
            return {"msg": f"No permission to modify user_id={id}"}, \
                HTTPStatus.FORBIDDEN

        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=False)
        parser.add_argument("firstname", type=str, required=False)
        parser.add_argument("lastname", type=str, required=False)
        parser.add_argument("roles", type=str, required=False)
        parser.add_argument("password", type=str, required=False)
        parser.add_argument("organization_id", type=int, required=False)
        data = parser.parse_args()

        if data["firstname"]:
            user.firstname = data["firstname"]
        if data["lastname"]:
            user.lastname = data["lastname"]
        if data["password"]:
            user.password = data["password"]
        if data["roles"]:
            user.roles = data["roles"]
        if data["organization_id"]:
            if is_root:
                user.organization_id = data["organization_id"]
                log.warn(
                    f'Running as root and assigning (new) '
                    f'organization_id={data["organization_id"]}'
                )
            else:
                log.error('Current user cannot assign new organizations!')

        try:
            user.save()
        except sqlalchemy.exc.IntegrityError as e:
            log.error(e)
            user.session.rollback()

        return user, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_user_with_id.yaml")),
               endpoint='user_with_id')
    def delete(self, id):

        user = db.User.get(id)
        if not user:
            return {"msg": "user id={} not found".format(id)}, \
                HTTPStatus.NOT_FOUND
        is_root = g.user.username == 'root'
        if user.organization_id != g.user.organization_id and not is_root:
            log.warning(f"user {g.user.id} has tried to delete user {user.id} "
                        f"but does not have the required permissions")
            return {"msg": "you do not have permission to modify user"
                    f" id={id}"}, \
                HTTPStatus.FORBIDDEN

        user.delete()
        log.info(f"user id={id} is removed from the database")
        return {"msg": f"user id={id} is removed from the database"}, \
            HTTPStatus.OK
