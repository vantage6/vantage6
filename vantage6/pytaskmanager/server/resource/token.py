# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/token'
"""
from __future__ import print_function, unicode_literals

import logging
import pytaskmanager.server as server

from pytaskmanager.server import db
from flask import request, g
from flask_restful import Resource, abort
from flask_jwt_extended import jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(Token, path)
    api.add_resource(RefreshToken, path+'/refresh')


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Token(Resource):
    """resource for api/token"""

    @staticmethod
    def post():
        """authenticate"""
        if not request.is_json:
            log.warning('POST request without JSON body.')
            log.warning(request.headers)
            log.warning(request.data)
            return {"msg": "Missing JSON in request"}, 400  # Bad Request

        username = request.json.get('username', None)
        password = request.json.get('password', None)
        api_key = request.json.get('api_key', None)

        # user login
        if username and password:
            log.info("trying to login '{}'".format(username))

            if db.User.username_exists(username):
                user = db.User.getByUsername(username)

                if not user.check_password(password):
                    return {"msg": "password not valid"}, 401

            else:
                return {"msg": "username does not exist"}, 401

            ret = {
                'access_token': create_access_token(user),
                'refresh_token': create_refresh_token(user),
                'user_url': server.api.url_for(server.resource.user.User, user_id=user.id),
                'refresh_url': server.api.url_for(RefreshToken),
            }

            log.info("Successful login for '{}'".format(username))
            return ret, 200

        # node login
        elif api_key:
            log.info("trying to authenticate node with api_key")

            node = db.Node.get_by_api_key(api_key)

            if node:
                ret = {
                    'access_token': create_access_token(node),
                    'refresh_token': create_refresh_token(node),
                    'node_url': server.api.url_for(server.resource.node.Node, uid=node.id),
                    'refresh_url': server.api.url_for(RefreshToken),
                }
                log.info("Authenticated as node '{}' ({})".format(node.id, node.name))
                return ret, 200

            else:
                log.info("Invalid API-key! Aborting!")
                return abort(401, message="Invalid API-key")

        # bad request
        return {"msg": "no API key or user/password combination provided"}, 400


class RefreshToken(Resource):

    @jwt_refresh_token_required
    def post(self):
        """Create a token from a refresh token."""
        user_or_node_id = get_jwt_identity()
        log.info('Refreshing token for user or node "{}"'.format(user_or_node_id))
        user_or_node = db.Authenticatable.get(user_or_node_id)
        ret = {'access_token': create_access_token(user_or_node)}

        return ret, 200
