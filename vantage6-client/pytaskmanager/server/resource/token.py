# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/token'
"""
from __future__ import print_function, unicode_literals

import logging

from flask import request, jsonify
from flask_restful import Resource
from flask_jwt_extended import jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from http import HTTPStatus
from pytaskmanager import server
from pytaskmanager.server import db

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Token,
        path,
        endpoint='token'
    )

    api.add_resource(
        RefreshToken,
        path+'/refresh',
        endpoint='refresh_token'
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Token(Resource):
    """resource for api/token"""

    @staticmethod
    @swag_from("swagger\post_token.yaml", endpoint='token')
    def post():
        """Authenticate user or node"""
        if not request.is_json:
            log.warning('POST request without JSON body.')
            return {"msg": "Missing JSON in request"}, HTTPStatus.BAD_REQUEST

        username = request.json.get('username', None)
        password = request.json.get('password', None)
        api_key = request.json.get('api_key', None)

        if username and password:
            user, code = Token.user_login(username, password)
            if code is not HTTPStatus.OK:  # login failed
                return user, code

            token = create_access_token(user)
            ret = {
                'access_token': token,
                'refresh_token': create_refresh_token(user),
                'user_url': server.api.url_for(server.resource.user.User, user_id=user.id),
                'refresh_url': server.api.url_for(RefreshToken),
            }

            return ret, HTTPStatus.OK, {'jwt-token': token}

        elif api_key:
            log.info("trying to authenticate node with api_key")
            node = db.Node.get_by_api_key(api_key)
            if node:
                ret = {
                    'access_token': create_access_token(node),
                    'refresh_token': create_refresh_token(node),
                    'node_url': server.api.url_for(server.resource.node.Node, id=node.id),
                    'refresh_url': server.api.url_for(RefreshToken),
                }
                log.info("Authenticated as node '{}' ({})".format(node.id, node.name))
                return ret, HTTPStatus.OK

            else:
                msg = "Invalid API-key!"
                log.error(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED

        else:
            return {"msg": "no API key or user/password combination provided"}, 400

    @staticmethod
    def user_login(username, password):
        """Returns user or message in case of failed login attempt"""
        log.info("trying to login '{}'".format(username))

        if db.User.username_exists(username):
            user = db.User.getByUsername(username)
            if not user.check_password(password):
                msg = "password for username={} is invalid".format(username)
                log.error(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED
        else:
            msg = "username={} does not exist".format(username)
            log.error(msg)
            return {"msg": msg}, HTTPStatus.UNAUTHORIZED

        log.info("Successful login for '{}'".format(username))
        return user, HTTPStatus.OK


class RefreshToken(Resource):

    @jwt_refresh_token_required
    @swag_from("swagger\post_token_refresh.yaml", endpoint='refresh_token')
    def post(self):
        """Create a token from a refresh token."""
        user_or_node_id = get_jwt_identity()
        log.info('Refreshing token for user or node "{}"'.format(user_or_node_id))
        user_or_node = db.Authenticatable.get(user_or_node_id)
        ret = {'access_token': create_access_token(user_or_node)}

        return ret, HTTPStatus.OK
