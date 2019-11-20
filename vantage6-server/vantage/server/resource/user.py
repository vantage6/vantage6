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

from vantage.server import db
from vantage.server.resource import with_user, only_for
from vantage.server.resource._schema import UserSchema

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
        all_users = db.User.get(id)

        if not id:
            if "root" in g.user.roles:
                return self.user_schema.dump(all_users, many=True).data
            else:
                return self.user_schema.dump(
                    [user for user in all_users if user.id == g.user.organization_id], many=True
                ).data

        else:
            # TODO check if this user can be viewed
            if not all_users:
                return {"msg": "user id={} is not found".format(id)}, HTTPStatus.NOT_FOUND
            else:
                return self.user_schema.dump(all_users, many=False)

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
        data = parser.parse_args()

        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists"}, HTTPStatus.BAD_REQUEST

        user = db.User(
            username=data["username"],
            firstname=data["firstname"],
            lastname=data["lastname"],
            roles=data["roles"],
            organization_id=g.user.organization_id
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
        data = parser.parse_args()

        if data["username"]:
            user.username = data["username"]
        if data["firstname"]:
            user.firstname = data["firstname"]
        if data["lastname"]:
            user.lastname = data["lastname"]
        if data["password"]:
            user.set_password(data["password"])
        if data["roles"]:
            user.roles = data["roles"]

        user.save()
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
