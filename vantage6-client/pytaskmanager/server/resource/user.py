# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/user'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from flask import g
from flask.ext.api import status
from flask.
from flask_restful import reqparse
from pytaskmanager.server.resource._schema import UserSchema

from .. import db

from . import with_user_or_node, with_user

def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(User,
        path,
        path + '/<int:user_id>',
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class User(Resource):

    user_schema = UserSchema()

    @with_user
    def get(self, user_id=None):
        """Return user details."""
        all_users = db.User.get(user_id)

        if not user_id:
            if "admin" in g.user.roles:
                return self.user_schema.dump(all_users, many=True).data
            else:
                return self.user_schema.dump(
                    [user for user in all_users if user.id == g.user.organization_id], many=True
                ).data

        else:
            if not all_users:
                return {"msg": "user id={} is not found".format(user_id)}, status
            else:
                return self.user_schema.dump(all_users, many=False)

    @with_user
    def post(self, user_id=None):
        """Create a new User."""

        if user_id:
            return {"msg": "id specified, but this is not allowed when using the POST method"}

        parser = reqparse.RequestParser()
        parser.add_argument("username", type=str, required=True, help="This field is required")
        parser.add_argument("firstname", type=str, required=True, help="This field is required")
        parser.add_argument("lastname", type=str, required=True, help="This field is required")
        parser.add_argument("roles", type=str, required=True, help="This field is required")
        parser.add_argument("password", type=str, required=True, help="This field is required")
        data = parser.parse_args()

        if db.User.username_exists(data["username"]):
            return {"msg": "username already exists"}, 200

        user = db.User(
            username=data["username"],
            firstname=data["firstname"],
            lastname=data["lastname"],
            roles=data["roles"],
            organization_id=g.user.organization_id
        )
        user.set_password(data["password"])
        user.save()

        return self.user_schema(user), 201

    @with_user
    def patch(self, user_id=None):
        if not user_id:
            return {"msg": "to update an user you need to specify an id"}, 400

        user = db.User.get(user_id)

        if not user:
            return {"msg": "user id={} not found".format(user_id)}, 404
        if user.organization_id != g.user.organization_id and g.user.roles != "admin":
            return {"msg": "you do not have permission to modify user id={}".format(user_id)}, 403

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
        return user

    @with_user
    def delete(self, user_id=None):
        if not user_id:
            return {"msg": "to delete an user you need to specify an id"}, 400

        user = db.User.get(user_id)
        if not user:
            return {"msg": "user id={} not found".format(user_id)}, 404
        if user.organization_id != g.user.organization_id and g.user.roles != "admin":
            log.warning(
                "user {} has tried to delete user {} but does not have the required permissions".format(
                    g.user.id,
                    user.id
                )
            )
            return {"msg": "you do not have permission to modify user id={}".format(user_id)}, 403

        user.delete()
        log.info("user id={} is removed from the database".format(user_id))
        return {"msg": "user id={} is removed from the database".format(user_id)}, 200
