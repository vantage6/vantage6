import logging
from http import HTTPStatus

from flask import request
from flask_restful import Api
from marshmallow import ValidationError

from vantage6.common import logger_name, generate_apikey
from vantage6.server import db
from vantage6.server.model.rule import Operation
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server.resource.common.input_schema import ResetAPIKeyInputSchema

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the recover resource.

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
    log.info(f'Setting up "{path}" and subdirectories')
    api.add_resource(
        ResetAPIKey,
        path + "/node",
        endpoint="reset_api_key",
        methods=("POST",),
        resource_class_kwargs=services,
    )


reset_api_key_schema = ResetAPIKeyInputSchema()

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


class ResetAPIKey(ServicesResources):
    """User can reset API key."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)

        # obtain permissions to check if user is allowed to modify nodes
        self.r = getattr(self.permissions, "node")

    @with_user
    def post(self):
        """Reset a node's API key
        ---
        description: >-
            If a node's API key is lost, this route can be used to obtain a new
            API key.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Node|Global|Edit|❌|❌|Reset API key of node specified by id|\n
            |Node|Organization|Edit|❌|❌|Reset API key of node specified by
            id which is part of your organization |\n

            Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: ID of node whose API key is to be reset

        responses:
            200:
                description: Ok
            400:
                description: ID missing from json body
            401:
                description: Unauthorized
            404:
                description: Node not found

        security:
            - bearerAuth: []

        tags: ["Account recovery"]
        """
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = reset_api_key_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        id_ = body["id"]
        node = db.Node.get(id_)
        if not node:
            return {"msg": f"Node id={id_} is not found!"}, HTTPStatus.NOT_FOUND

        # check if user is allowed to edit the node
        if not self.r.allowed_for_org(Operation.EDIT, node.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # all good, change API key
        log.info(f"Successful API key reset for node {id}")
        api_key = generate_apikey()
        node.api_key = api_key
        node.save()

        return {"api_key": api_key}, HTTPStatus.OK
