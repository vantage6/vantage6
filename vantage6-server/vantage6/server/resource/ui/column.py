from http import HTTPStatus

import logging
from flask_restful import Api
from flask import request

from vantage6.common import logger_name
from vantage6.common.globals import BASIC_PROCESSING_IMAGE
from vantage6.server import db
from vantage6.server.permission import RuleCollection, Operation as P
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server.resource.common.input_schema import ColumnNameInputSchema
from vantage6.server.resource.task import Tasks


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the column resource.

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
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        ColumnNames,
        path,
        endpoint="column_names_without_id",
        methods=("POST",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
column_name_input_schema = ColumnNameInputSchema()


class ColumnNames(ServicesResources):
    """Resource for requesting column names from a node database."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        # Use task permissions for this resource
        self.r_task: RuleCollection = getattr(self.permissions, "task")

    # TODO this endpoint currently requires the user to provide the
    # organization details (including input) for the task to retrieve the
    # column names. When the method name is stored in the database, and is thus
    # no longer encrypted, we can remove this requirement.
    @with_user
    def post(self):
        """Create request to get column names of a database. This is used in
        the user interface to show the user which columns are available.
        ---
        description: >-
          Returns a list of column names.\n

          Accessible to users based on their permissions to create tasks for
          the collaboration for which the request column names.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  db_label:
                    type: string
                    description: The label of the database whose column names
                      are requested
                  collaboration_id:
                    type: integer
                    description: The collaboration id for which database
                      columns are requested
                  organizations:
                    type: array
                    description: The organizations that should execute the
                      task. Each organization should be defined by a dictionary
                      with the `id` key and `input` data for a task.
                  sheet_name:
                    type: string
                    description: The name of the worksheet for which you want
                      to read the columns. Required for Excel files.
                  query:
                    type: string
                    description: The query that is used to obtain the data.
                      Required for SQL and SparQL databases.

        responses:
          201:
            description: Ok
          400:
            description: Non-allowed or wrong parameter values
          401:
            description: Unauthorized
          404:
            description: Collaboration not found

        security:
            - bearerAuth: []

        tags: ["Task"]
        """
        data = request.get_json()

        # validate request body
        errors = column_name_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        collaboration_id = data["collaboration_id"]
        collaboration = db.Collaboration.get(collaboration_id)
        if not collaboration:
            return {
                "msg": f"Collaboration id={collaboration_id} not found!"
            }, HTTPStatus.NOT_FOUND

        # check if user has permission to create a task for this collaboration:
        # that determines if the user is allowed to request column names
        if not self.r_task.can_for_col(P.CREATE, collaboration_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # check if the column names are already available in the database
        # through shared node details.
        label = data["db_label"]
        colnames = []
        for node in collaboration.nodes:
            for record in node.config:
                if record.key == f"columns_{label}":
                    colnames.append(record.value)
            # note this indent: if one node has the column names, we assume
            # that all nodes have the column names. Otherwise it will just
            # lead to an error for the other nodes.
            if colnames:
                return {"columns": colnames}, HTTPStatus.OK

        # Column names not yet available, create new task to request column
        # names
        databases = [{"label": label}]
        if data.get("sheet_name"):
            databases[0]["sheet_name"] = data["sheet_name"]
        if data.get("query"):
            databases[0]["query"] = data["query"]
        return Tasks.post_task(
            data={
                "collaboration_id": collaboration_id,
                "name": "get_column_names",
                "image": BASIC_PROCESSING_IMAGE,
                "organizations": data["organizations"],
                "databases": databases,
            },
            socketio=self.socketio,
            rules=self.r_task,
        )
