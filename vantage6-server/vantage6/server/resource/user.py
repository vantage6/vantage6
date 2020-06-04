# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/user'
"""
from __future__ import print_function, unicode_literals

import logging

from flask_restful import Resource
from flask import g
from flask_restful import reqparse
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

import sqlalchemy.exc

from vantage6.server import db
from vantage6.server.resource import with_user, only_for
from vantage6.server.resource._schema import UserSchema

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        User,
        path,
        endpoint='user_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        User,
        path + '/<int:id>',
        endpoint='user_with_id',
        methods=('GET', 'PATCH', 'DELETE')
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class User(Resource):

    user_schema = UserSchema()

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/get_user_with_id.yaml")), endpoint='user_with_id')
    @swag_from(str(Path(r"swagger/get_user_without_id.yaml")), endpoint='user_without_id')
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
    @swag_from(str(Path(r"swagger/post_user_without_id.yaml")), endpoint='user_without_id')
    def post(self):
        """Create a new User."""

        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=True, help="This field is required")
        parser.add_argument("firstname", type=str, required=True, help="This field is required")
        parser.add_argument("lastname", type=str, required=True, help="This field is required")
        parser.add_argument("roles", type=str, required=True, help="This field is required")
        parser.add_argument("password", type=str, required=True, help="This field is required")
        parser.add_argument("organization_id", type=int, required=False, help="This is only used if you're root")
        data = parser.parse_args()

        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists"}, HTTPStatus.BAD_REQUEST

        if data["username"] == 'root':
            msg = {"msg": "You're funny! You can't create root!?"}
            return msg, HTTPStatus.BAD_REQUEST

        roles = data['roles'].split(',')
        if 'root' in roles:
            msg = {"msg": "You're funny! You can't assign the role 'root'!?"}
            return msg, HTTPStatus.BAD_REQUEST

        if g.user.username == 'root':
            organization_id = data['organization_id']
            log.warn(f'Running as root and creating user for organization_id={organization_id}')
        else:
            organization_id = g.user.organization_id
            log.warn(f'Creating user for organization_id={organization_id}') 

        # Ok, looks like we got most of the security hazards out of the way
        user = db.User(
            username=data["username"],
            firstname=data["firstname"],
            lastname=data["lastname"],
            roles=data["roles"],
            organization_id=organization_id
        )

        user.set_password(data["password"])
        user.save()

        return self.user_schema.dump(user), HTTPStatus.CREATED
    @with_user
    @swag_from(str(Path(r"swagger/patch_user_with_id.yaml")), endpoint='user_with_id')
    def patch(self, id):

        user = db.User.get(id)

        if not user:
            return {"msg": "user id={} not found".format(id)}, HTTPStatus.NOT_FOUND
        if user.organization_id != g.user.organization_id and g.user.roles != "admin":
            return {"msg": "you do not have permission to modify user id={}".format(id)}, HTTPStatus.FORBIDDEN

        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=False, help="This field is required")
        parser.add_argument("firstname", type=str, required=False, help="This field is required")
        parser.add_argument("lastname", type=str, required=False, help="This field is required")
        parser.add_argument("roles", type=str, required=False, help="This field is required")
        parser.add_argument("password", type=str, required=False, help="This field is required")
        parser.add_argument("organization_id", type=int, required=False, help="This is only used if you're root")
        data = parser.parse_args()

        # Username cannot be changed once set?
        # if data["username"]:
        #     user.username = data["username"]
        if data["firstname"]:
            user.firstname = data["firstname"]
        if data["lastname"]:
            user.lastname = data["lastname"]
        if data["password"]:
            user.set_password(data["password"])
        if data["roles"]:
            user.roles = data["roles"]
        if data["organization_id"]:
            if g.user.username == 'root':
                user.organization_id = data["organization_id"]
                log.warn(f'Running as root and assigning (new) organization_id={data["organization_id"]}')
            else:
                log.error('Current user cannot assign new organizations!')

        try:
            user.save()
        except sqlalchemy.exc.IntegrityError as e:
            log.error(e)
            user.session.rollback()

        return user, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_user_with_id.yaml")), endpoint='user_with_id')
    def delete(self, id):

        user = db.User.get(id)
        if not user:
            return {"msg": "user id={} not found".format(id)}, HTTPStatus.NOT_FOUND
        if user.organization_id != g.user.organization_id and g.user.roles != "admin":
            log.warning(
                "user {} has tried to delete user {} but does not have the required permissions".format(
                    g.user.id,
                    user.id
                )
            )
            return {"msg": "you do not have permission to modify user id={}".format(id)}, HTTPStatus.FORBIDDEN

        user.delete()
        log.info("user id={} is removed from the database".format(id))
        return {"msg": "user id={} is removed from the database".format(id)}, HTTPStatus.OK
