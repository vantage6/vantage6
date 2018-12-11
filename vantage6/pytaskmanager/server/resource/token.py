# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/token'
"""
from __future__ import print_function, unicode_literals

import logging

from flask import request, jsonify, g
from flask_restful import Resource
from flask_jwt_extended import jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from pytaskmanager import server
from pytaskmanager.server import db
from pytaskmanager.server.resource import with_node

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Token,
        path,
        endpoint='token',
        methods=('POST',)
    )

    api.add_resource(
        RefreshToken,
        path+'/refresh',
        endpoint='refresh_token',
        methods=('POST',)
    )

    api.add_resource(
        ContainerToken,
        path+'/container',
        endpoint='container_token',
        methods=('POST',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Token(Resource):
    """resource for api/token"""

    @staticmethod
    @swag_from(str(Path(r"swagger/post_token.yaml")), endpoint='token')
    def post():
        """Authenticate user or node"""
        log.debug("POST /token")

        if not request.is_json:
            log.warning('POST request without JSON body.')
            return {"msg": "Missing JSON in request"}, HTTPStatus.BAD_REQUEST

        # log.debug("got some json:")
        # log.debug(request.json)
        # log.debug("can print it too")

        username = request.json.get('username', None)
        password = request.json.get('password', None)
        api_key = request.json.get('api_key', None)

        log.debug(f"username: '{username}'")
        # log.debug(f"api_key: '{api_key}'")

        if username and password:
            log.debug(f"trying to login {username}")
            user, code = Token.user_login(username, password)
            if code is not HTTPStatus.OK:  # login failed
                log.error(f"Could not login user '{username}'")
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
            log.debug("trying to authenticate node with api_key")

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
            msg = "no API key or user/password combination provided"
            log.error(msg)
            return {"msg": msg}, 400

        log.error("this can't be right ...")


    @staticmethod
    def user_login(username, password):
        """Returns user or message in case of failed login attempt"""
        log.info("trying to login '{}'".format(username))

        if db.User.username_exists(username):
            user = db.User.getByUsername(username)
            if not user.check_password(password):
                msg = f"password for '{username}' is invalid"
                log.error(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED
        else:
            msg = "username '{}' does not exist".format(username)
            log.error(msg)
            return {"msg": msg}, HTTPStatus.UNAUTHORIZED

        log.info("Successful login for '{}'".format(username))
        return user, HTTPStatus.OK


class RefreshToken(Resource):

    @jwt_refresh_token_required
    @swag_from(str(Path(r"swagger/post_token_refresh.yaml")), endpoint='refresh_token')
    def post(self):
        """Create a token from a refresh token."""
        user_or_node_id = get_jwt_identity()
        log.info('Refreshing token for user or node "{}"'.format(user_or_node_id))
        user_or_node = db.Authenticatable.get(user_or_node_id)
        ret = {'access_token': create_access_token(user_or_node)}

        return ret, HTTPStatus.OK

class ContainerToken(Resource):
    
    @with_node
    @swag_from(str(Path(r"swagger/post_token_container.yaml")), endpoint='container_token')
    def post(self):
        """Create a token for a container running on a node."""
        log.debug("POST /token/container")
        
        data = request.get_json()
        
        task_id = data.get("task_id")
        db_task = db.Task.get(task_id)
        claim_image = data.get("image")

        # verify that task the token is requested for exists
        if claim_image != db_task.image:
            log.warning(f"node {g.node.id} attemts to generate key for image {claim_image} \
                        that does not belong to task {task_id}")
            return {"msg": "image and task do no match"}, HTTPStatus.UNAUTHORIZED
        
        # check if the node is in the collaboration to which the task is enlisted
        if g.node.collaboration_id != db_task.collaboration_id:
            log.warning(f"node {g.node.id} attemts to generate key for task {task_id} \
                        which he doesn't own")
            return {"msg": "you do not own that task"}, HTTPStatus.UNAUTHORIZED
        
        # validate that the task not has been finished yet
        if db_task.complete():
            log.warning(f"node {g.node.id} attempts to generate a key for completed \
            task {task_id}")
            return {"msg": "task is already finished!"}, HTTPStatus.BAD_REQUEST
        
        # container token can be identified by its node_id, 
        # task_id, collaboration_id and image_id
        container = {
            "node": g.node.id,
            "collaboration": g.node.collaboration_id,
            "task": task_id,
            "image": claim_image
        }

        return {'container_token': create_access_token(container)}, HTTPStatus.OK
        