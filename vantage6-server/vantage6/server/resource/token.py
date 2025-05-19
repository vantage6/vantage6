"""
Resources below '/<api_base>/token'
"""

import logging
import pyotp
import json

from flask import request, g
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    create_refresh_token,
    get_jwt_identity,
)
from flask_restful import Api
from marshmallow import ValidationError
from http import HTTPStatus

from vantage6 import server
from vantage6.common.enum import TaskStatus
from vantage6.common.globals import MAIN_VERSION_NAME
from vantage6.server import db
from vantage6.server.model.user import User
from vantage6.server.resource import with_node, ServicesResources
from vantage6.server.resource.common.input_schema import (
    TokenAlgorithmInputSchema,
    TokenNodeInputSchema,
    TokenUserInputSchema,
)
from vantage6.server.resource import with_user

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the token resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        NodeToken,
        path + "/node",
        endpoint="node_token",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        ContainerToken,
        path + "/container",
        endpoint="container_token",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        RefreshToken,
        path + "/refresh",
        endpoint="refresh_token",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        ValidateToken,
        path + "/user/validate",
        endpoint="validate_user_token",
        methods=("POST",),
        resource_class_kwargs=services,
    )


user_token_input_schema = TokenUserInputSchema()
node_token_input_schema = TokenNodeInputSchema()
algorithm_token_input_schema = TokenAlgorithmInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


class NodeToken(ServicesResources):
    def post(self):
        """Login node
        ---
        description: >-
          Allows node to sign in using a unique API key. If the login is
          successful this returns a dictionary with access and refresh tokens
          for the node as well as a node_url and a refresh_url.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Node'

        responses:
          200:
            description: Ok, authenticated
          400:
            description: No API key provided in request body.
          401:
            description: Invalid API key

        tags: ["Authentication"]
        """
        log.debug("Authenticate Node using api key")

        body = request.get_json(silent=True)
        # validate request body
        try:
            body = node_token_input_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # Check JSON body
        api_key = request.json.get("api_key")
        node = db.Node.get_by_api_key(api_key)
        if not node:  # login failed
            log.error("Api key is not recognized")
            return {"msg": "Api key is not recognized!"}, HTTPStatus.UNAUTHORIZED

        token = _get_token_dict(node, self.api)

        log.info(f"Succesfull login as node '{node.id}' ({node.name})")
        return token, HTTPStatus.OK, {"jwt-token": token["access_token"]}


class ContainerToken(ServicesResources):
    @with_node
    def post(self):
        """Algorithm container login
        ---
        description: >-
          Generate token for the algorithm container of a specific task.\n

          Not available to users; only for authenticated nodes.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/ContainerToken'

        responses:
          200:
            description: Container token generated
          400:
            description: Task does not exist or is already completed
          401:
            description: Key request for invalid image or task

        tags: ["Authentication"]
        """
        log.debug("Creating a token for a container running on a node")

        body = request.get_json(silent=True)
        # validate request body
        try:
            body = algorithm_token_input_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        task_id = body.get("task_id")
        claim_image = body.get("image")

        db_task = db.Task.get(task_id)
        if not db_task:
            log.warning(
                f"Node {g.node.id} attempts to generate key for task "
                f"{task_id} that does not exist"
            )
            return {"msg": "Parent task does not exist!"}, HTTPStatus.BAD_REQUEST

        # check if the node is in the collaboration to which the task is
        # enlisted
        if g.node.collaboration_id != db_task.collaboration_id:
            log.warning(
                "Node %s attempts to generate key for task %s which is outside its "
                "collaboration. Node is in collaboration %s, task in %s).",
                g.node.id,
                task_id,
                g.node.collaboration_id,
                db_task.collaboration_id,
            )
            return {
                "msg": "You are not within the collaboration"
            }, HTTPStatus.UNAUTHORIZED

        # verify that task the token is requested for exists
        collaboration = db.Collaboration.get(db_task.collaboration_id)
        if collaboration.session_restrict_to_same_image:
            if claim_image != db_task.image:
                log.warning(
                    "Node %s attempts to generate key for image %s that does not belong"
                    " to task %s. This is not allowed because this collaboration has "
                    " the 'session_restrict_to_same_image' option set to True.",
                    g.node.id,
                    claim_image,
                    task_id,
                )
                return {"msg": "Image and task do no match"}, HTTPStatus.UNAUTHORIZED

        # validate that the task not has been finished yet
        if TaskStatus.has_finished(db_task.status):
            log.warning(
                "Node %s attempts to generate a key for completed task %s",
                g.node.id,
                task_id,
            )
            return {"msg": "Task is already finished!"}, HTTPStatus.BAD_REQUEST

        # We store the task metadata in the token, so the server can verify later on
        # that the container is allowed to access certain server resources.
        container = {
            "client_type": "container",
            "node_id": g.node.id,
            "organization_id": g.node.organization_id,
            "collaboration_id": g.node.collaboration_id,
            "study_id": db_task.study_id,
            "store_id": db_task.algorithm_store_id,
            "task_id": task_id,
            "image": claim_image,
            "databases": [
                {
                    "label": db_entry.label,
                    "type": db_entry.type_,
                    "dataframe_id": db_entry.dataframe_id,
                }
                for db_entry in db_task.databases
            ],
        }
        token = create_access_token(container, expires_delta=False)

        return {"container_token": token}, HTTPStatus.OK


class RefreshToken(ServicesResources):
    @jwt_required(refresh=True)
    def post(self):
        """Refresh token
        ---
        description: >-
          Refresh access token if the previous one is expired.\n

          Your refresh token must be present in the request headers to use
          this endpoint.

        responses:
          200:
            description: Token refreshed

        security:
          - bearerAuth: []

        tags: ["Authentication"]
        """
        user_or_node_id = get_jwt_identity()
        log.info(f'Refreshing token for user or node "{user_or_node_id}"')
        user_or_node = db.Authenticatable.get(user_or_node_id)

        return _get_token_dict(user_or_node, self.api), HTTPStatus.OK


class ValidateToken(ServicesResources):
    """Resource for /token/user/validate"""

    @with_user
    def post(self):
        """Validate a user token
        ---
        description: >-
          Validate that a user token is valid. This is used by external
          services such as an algorithm store to validate that a user token is
          valid.

        responses:
          200:
            description: Token is valid
          401:
            description: Token is invalid

        tags: ["Authentication"]
        """
        # TODO we should check the origin of the request. Only allow requests
        #  from whitelisted algorithm stores and only for users that are in
        # the right collaboration(s).

        # Note: if the token is invalid, the with_user decorator will return
        # an error response. So if we get here, the token is valid.
        return {
            "msg": "Token is valid",
            "user_id": g.user.id,
            "username": g.user.username,
            "email": g.user.email,
            "organization_id": g.user.organization_id,
        }, HTTPStatus.OK


def _get_token_dict(user_or_node: db.Authenticatable, api: Api) -> dict:
    """
    Create a dictionary with the tokens and urls for the user or node.

    Parameters
    ----------
    user_or_node : db.Authenticatable
        The user or node to create the tokens for.
    api : Api
        The api to create the urls for.
    """
    token_dict = {
        "access_token": create_access_token(user_or_node),
        "refresh_token": create_refresh_token(user_or_node),
        "refresh_url": api.url_for(RefreshToken),
    }
    if isinstance(user_or_node, db.User):
        token_dict["user_url"] = api.url_for(
            server.resource.user.User, id=user_or_node.id
        )
    else:
        token_dict["node_url"] = api.url_for(
            server.resource.node.Node, id=user_or_node.id
        )
    return token_dict
