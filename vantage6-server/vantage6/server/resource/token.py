"""
Resources below '/<api_base>/token'
"""

import logging
from http import HTTPStatus

import jwt
from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError

from vantage6.common.enum import AlgorithmStepType, TaskStatus

from vantage6.server import db
from vantage6.server.resource import ServicesResources, with_node
from vantage6.server.resource.common.input_schema import TokenAlgorithmInputSchema

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
        ContainerToken,
        path + "/container",
        endpoint="container_token",
        methods=("POST",),
        resource_class_kwargs=services,
    )


algorithm_token_input_schema = TokenAlgorithmInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


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

        # Check wether the action of the task is of type 'central_compute' as only
        # the central task requires to communicate with the server.
        if db_task.action != AlgorithmStepType.CENTRAL_COMPUTE:
            log.warning(
                "Node %s attempts to generate key for task %s which is not a "
                "central compute task.",
                g.node.id,
                task_id,
            )
            return {
                "msg": "Task is not a central compute task"
            }, HTTPStatus.UNAUTHORIZED

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
                return {
                    "msg": "This collaboration only allows a single image per session. "
                    "You cannot create a task with a different image."
                }, HTTPStatus.UNAUTHORIZED

        # validate that the task not has been finished yet
        if TaskStatus.has_finished(db_task.status):
            log.warning(
                "Node %s attempts to generate a key for completed task %s",
                g.node.id,
                task_id,
            )
            return {"msg": "Task is already finished!"}, HTTPStatus.BAD_REQUEST

        # Group databases by position and convert to list of lists
        databases_by_position = {}
        for db_entry in db_task.databases:
            pos = db_entry.position
            if pos not in databases_by_position:
                databases_by_position[pos] = []
            databases_by_position[pos].append(
                {
                    "label": db_entry.label,
                    "type": db_entry.type_,
                    "dataframe_id": db_entry.dataframe_id,
                }
            )
        databases = [
            databases_by_position[pos] for pos in sorted(databases_by_position.keys())
        ]

        # We store the task metadata in the token, so the server can verify later on
        # that the container is allowed to access certain server resources.
        container = {
            "vantage6_client_type": "container",
            "node_id": g.node.id,
            "organization_id": g.node.organization_id,
            "collaboration_id": g.node.collaboration_id,
            "study_id": db_task.study_id,
            "store_id": db_task.algorithm_store_id,
            "session_id": db_task.session_id,
            "task_id": task_id,
            "image": claim_image,
            "databases": databases,
        }

        token = jwt.encode(
            {"sub": container}, self.config["jwt_secret_key"], algorithm="HS256"
        )

        return {"container_token": token}, HTTPStatus.OK
