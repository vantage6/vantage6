# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/token'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource, abort
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

import sqlalchemy

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = os.path.join(API_BASE, module_name)
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(Token, path)
    api.add_resource(RefreshToken, path+'/refresh')

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Token(Resource):

    def post(self):
        """Create a new Token."""
        if not request.is_json:
            log.warning('POST request without JSON body.')
            log.warning(request.headers)
            log.warning(request.data)
            return {"msg": "Missing JSON in request"}, 400

        username = request.json.get('username', None)
        password = request.json.get('password', None)
        api_key = request.json.get('api_key', None)

        if username and password:
            log.info("trying to login '{}'".format(username))
            user = db.User.getByUsername(username)

            if not user.check_password(password):
                return {"msg": "Computer says no!"}, 401

            ret = {
                'access_token': create_access_token(user),
                'refresh_token': create_refresh_token(user),
            }

            return ret, 200

        elif api_key:
            try:
                client = db.Client.getByApiKey(api_key)

                ret = {
                    'access_token': create_access_token(client),
                    'refresh_token': create_refresh_token(client),
                }

            # FIXME: should not depend on sqlalchemy errors
            except sqlalchemy.orm.exc.NoResultFound as e:
                return abort(401, message="Invalid API-key!")

            return ret, 200

        msg = "No username and/or pasword nor API-key!? Aren't you forgetting something?"
        log.error((msg, 404))
        log.error(request.get_json())
        return {"msg": msg}, 404


class RefreshToken(Resource):

    @jwt_refresh_token_required
    def post(self):
        """Create a token from a refresh token."""
        user_or_client_id = get_jwt_identity()
        log.info('Refreshing token for user or client "{}"'.format(user_or_client_id))
        ret = None
        
        user_or_client = db.Authenticatable.get(user_or_client_id)
        ret = {'access_token': create_access_token(user_or_client)}

        return ret, 200
