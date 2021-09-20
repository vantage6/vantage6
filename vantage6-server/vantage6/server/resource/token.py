# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/token'
"""
from __future__ import print_function, unicode_literals

import logging

from flask import request, g
from flask_jwt_extended import (
    jwt_refresh_token_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity
)
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6 import server
from vantage6.server import db
from vantage6.server.resource import (
    only_for,
    ServicesResources
)

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        UserToken,
        path+'/user',
        endpoint='user_token',
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        NodeToken,
        path+'/node',
        endpoint='node_token',
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        ContainerToken,
        path+'/container',
        endpoint='container_token',
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        RefreshToken,
        path+'/refresh',
        endpoint='refresh_token',
        methods=('POST',),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class UserToken(ServicesResources):
    """resource for api/token"""

    @swag_from(str(Path(r"swagger/post_token_user.yaml")),
               endpoint='user_token')
    def post(self):
        """Authenticate user or node"""
        log.debug("Authenticate user using username and password")

        if not request.is_json:
            log.warning('Authentication failed because no JSON body was '
                        'provided!')
            return {"msg": "Missing JSON in request"}, HTTPStatus.BAD_REQUEST

        # Check JSON body
        username = request.json.get('username', None)
        password = request.json.get('password', None)
        if not username and password:
            msg = "Username and/or password missing in JSON body"
            log.error(msg)
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        log.debug(f"Trying to login {username}")
        user, code = self.user_login(username, password)
        if code is not HTTPStatus.OK:  # login failed
            log.error(f"Incorrect username/password combination for "
                      f"user='{username}'")
            return user, code

        token = create_access_token(user)

        ret = {
            'access_token': token,
            'refresh_token': create_refresh_token(user),
            'user_url': self.api.url_for(server.resource.user.User,
                                         id=user.id),
            'refresh_url': self.api.url_for(RefreshToken),
        }

        log.info(f"Succesfull login from {username}")
        return ret, HTTPStatus.OK, {'jwt-token': token}

    @staticmethod
    def user_login(username, password):
        """Returns user or message in case of failed login attempt"""
        log.info(f"trying to login '{username}'")

        if db.User.username_exists(username):
            user = db.User.get_by_username(username)
            if not user.check_password(password):
                msg = f"password for '{username}' is invalid"
                log.error(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED
        else:
            msg = f"username '{username}' does not exist"
            log.error(msg)
            return {"msg": msg}, HTTPStatus.UNAUTHORIZED

        return user, HTTPStatus.OK


class NodeToken(ServicesResources):

    @swag_from(str(Path(r"swagger/post_token_node.yaml")),
               endpoint='node_token')
    def post(self):
        """Authenticate as Node."""
        log.debug("Authenticate Node using api key")

        if not request.is_json:
            log.warning('Authentication failed because no JSON body was '
                        'provided!')
            return {"msg": "Missing JSON in request"}, HTTPStatus.BAD_REQUEST

        # Check JSON body
        api_key = request.json.get('api_key', None)
        if not api_key:
            msg = "api_key missing in JSON body"
            log.error(msg)
            return {"msg": msg}, HTTPStatus.BAD_REQUEST

        node = db.Node.get_by_api_key(api_key)

        if not node:  # login failed
            log.error("Api key is not recognized")
            return {"msg": "Api key is not recognized!"}

        token = create_access_token(node)
        ret = {
            'access_token': create_access_token(node),
            'refresh_token': create_refresh_token(node),
            'node_url': self.api.url_for(server.resource.node.Node,
                                         id=node.id),
            'refresh_url': self.api.url_for(RefreshToken),
        }

        log.info(f"Succesfull login as node '{node.id}' ({node.name})")
        return ret, HTTPStatus.OK, {'jwt-token': token}


class ContainerToken(ServicesResources):

    @only_for(['node'])
    @swag_from(str(Path(r"swagger/post_token_container.yaml")),
               endpoint='container_token')
    def post(self):
        """Create a token for a container running on a node."""
        log.debug("Creating a token for a container running on a node")

        data = request.get_json()

        task_id = data.get("task_id")
        claim_image = data.get("image")
        db_task = db.Task.get(task_id)
        if not db_task:
            log.warning(f"Node {g.node.id} attempts to generate key for task "
                        f"{task_id} that does not exist")
            return {"msg": "Master task does not exist!"}, \
                HTTPStatus.BAD_REQUEST

        # verify that task the token is requested for exists
        if claim_image != db_task.image:
            log.warning(
                f"Node {g.node.id} attemts to generate key for image "
                f"{claim_image} that does not belong to task {task_id}."
            )
            return {"msg": "Image and task do no match"}, \
                HTTPStatus.UNAUTHORIZED

        # check if the node is in the collaboration to which the task is
        # enlisted
        if g.node.collaboration_id != db_task.collaboration_id:
            log.warning(
                f"Node {g.node.id} attemts to generate key for task {task_id} "
                f"which is outside its collaboration "
                f"({g.node.collaboration_id}/{db_task.collaboration_id})."
            )
            return {"msg": "You are not within the collaboration"}, \
                HTTPStatus.UNAUTHORIZED

        # validate that the task not has been finished yet
        if db_task.complete:
            log.warning(f"Node {g.node.id} attempts to generate a key for "
                        f"completed task {task_id}")
            return {"msg": "Task is already finished!"}, HTTPStatus.BAD_REQUEST

        # container identity consists of its node_id,
        # task_id, collaboration_id and image_id
        container = {
            "type": "container",
            "node_id": g.node.id,
            "organization_id": g.node.organization_id,
            "collaboration_id": g.node.collaboration_id,
            "task_id": task_id,
            "image": claim_image
        }
        token = create_access_token(container, expires_delta=False)

        return {'container_token': token}, HTTPStatus.OK


class RefreshToken(ServicesResources):

    @jwt_refresh_token_required
    @swag_from(str(Path(r"swagger/post_token_refresh.yaml")),
               endpoint='refresh_token')
    def post(self):
        """Create a token from a refresh token."""
        user_or_node_id = get_jwt_identity()
        log.info(f'Refreshing token for user or node "{user_or_node_id}"')
        user_or_node = db.Authenticatable.get(user_or_node_id)
        ret = {'access_token': create_access_token(user_or_node)}

        return ret, HTTPStatus.OK
