import datetime as dt
import logging
from http import HTTPStatus
from socket import SocketIO

from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError

from vantage6.common import logger_name
from vantage6.common.enum import RunStatus, TaskStatus
from vantage6.common.globals import AuthStatus

from vantage6.server import db
from vantage6.server.permission import Operation, PermissionManager, Scope
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server.resource.common.input_schema import (
    KillNodeTasksInputSchema,
    KillTaskInputSchema,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the event resource.

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
        KillTask,
        api_base + "/kill/task",
        endpoint="kill_task",
        methods=("POST",),
        resource_class_kwargs=services,
    )

    api.add_resource(
        KillNodeTasks,
        api_base + "/kill/node/tasks",
        endpoint="kill_node_tasks",
        methods=("POST",),
        resource_class_kwargs=services,
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """
    add = permissions.appender(module_name)

    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.RECEIVE,
        description="view websocket events of your organization",
    )
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.RECEIVE,
        description="view websocket events of your collaborations",
    )
    add(
        scope=Scope.GLOBAL,
        operation=Operation.RECEIVE,
        description="view websocket events",
    )
    add(
        scope=Scope.ORGANIZATION,
        operation=Operation.SEND,
        description="send websocket events for your organization",
    )
    add(
        scope=Scope.COLLABORATION,
        operation=Operation.SEND,
        description="send websocket events for your collaborations",
    )
    add(
        scope=Scope.GLOBAL,
        operation=Operation.SEND,
        description="send websocket events to all collaborations",
    )


kill_task_schema = KillTaskInputSchema()
kill_node_tasks_schema = KillNodeTasksInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class KillTask(ServicesResources):
    """Provide endpoint to kill all containers executing a certain task"""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)

    @with_user
    def post(self):
        """Kill task specified by task id
        ---
        description: >-
          Kill a task that is currently being executed on a node.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Event|Global|Create|❌|❌|Create kill signal for any task|\n
          |Event|Collaboration|Create|❌|❌|
          Create kill signal for any task in your collaboration|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Task id which is to be killed

        responses:
          200:
            description: Ok
          404:
            description: Task not found or already completed
          401:
            description: Unauthorized
          400:
            description: No task id provided

        tags: ["Task"]
        """
        body = request.get_json(silent=True)

        # validate request body
        try:
            body = kill_task_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        id_ = body.get("id")
        task = db.Task.get(id_)
        if not task:
            return {"msg": f"Task id={id_} not found"}, HTTPStatus.NOT_FOUND

        if TaskStatus.has_finished(task.status):
            return {
                "msg": f"Task {id_} already finished with status "
                f"'{task.status}', so cannot kill it!"
            }, HTTPStatus.BAD_REQUEST

        # Check permissions. If someone doesn't have global permissions, we
        # check if their organization is part of the appropriate collaboration.
        if not self.r.s_glo.can():
            orgs = task.collaboration.organizations
            if not (self.r.s_col.can() and g.user.organization in orgs):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # call function to kill the task. This function is outside of the
        # endpoint as it is also used in other endpoints
        kill_task(task, self.socketio)

        return {
            "msg": "Nodes have been instructed to kill any containers running "
            f"for task {id_}."
        }, HTTPStatus.OK


class KillNodeTasks(ServicesResources):
    """Provide endpoint to kill all tasks on a certain node"""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)

    @with_user
    def post(self):
        """Kill all tasks on a node specified by node id
        ---
        description: >-
          Kill all tasks that are currently being executed on a certain node.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Event|Global|Create|❌|❌|Create kill signal for all tasks on any
          node|\n
          |Event|Collaboration|Create|❌|❌|Create kill signal for all tasks
          on any node in collaborations|\n
          |Event|Organization|Create|❌|❌|Create kill signal for all tasks on
          any node of own organization|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Node id on which tasks are to be killed

        responses:
          200:
            description: Ok
          404:
            description: Node not found
          401:
            description: Unauthorized
          400:
            description: No task id provided or node is not online

        tags: ["Task"]
        """
        body = request.get_json(silent=True)
        # validate request body
        try:
            body = kill_node_tasks_schema.load(body)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        id_ = body.get("id")
        node = db.Node.get(id_)
        if not node:
            return {"msg": f"Node id={id_} not found"}, HTTPStatus.NOT_FOUND

        if node.status != AuthStatus.ONLINE:
            return {
                "msg": f"Node {id_} is not online so cannot kill its tasks!"
            }, HTTPStatus.BAD_REQUEST

        # Check permissions. If someone doesn't have global permissions, we
        # check if their organization is part of the appropriate collaboration.
        if not self.r.s_glo.can():
            collab_orgs = node.collaboration.organizations
            if not (
                (self.r.s_col.can() and g.user.organization in collab_orgs)
                or (
                    self.r.s_org.can()
                    and node.organization_id == g.user.organization_id
                )
            ):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        self.socketio.emit(
            "kill_containers",
            {"node_id": node.id, "collaboration_id": node.collaboration_id},
            namespace="/tasks",
            room=f"collaboration_{node.collaboration_id}",
        )

        return {
            "msg": f"Node {node.id} has been instructed to kill all containers"
            " running on it."
        }, HTTPStatus.OK


def kill_task(task: db.Task, socket: SocketIO) -> None:
    """
    Send instructions to node(s) to kill a certain task

    Parameters
    ----------
    task: Task
        Task that should be killed
    socket: SocketIO
        SocketIO connection object to communicate kill instructions to node
    """
    # Gather runs and task ids of current task and child tasks
    child_runs = [r for child in task.children for r in child.runs]
    all_runs = task.runs + child_runs

    kill_list = [
        {
            "task_id": run.task_id,
            "run_id": run.id,
            "organization_id": run.organization_id,
        }
        for run in all_runs
    ]

    # emit socket event to the node to execute the container kills
    socket.emit(
        "kill_containers",
        {"kill_list": kill_list, "collaboration_id": task.collaboration.id},
        namespace="/tasks",
        room=f"collaboration_{task.collaboration_id}",
    )

    # set tasks and subtasks status to killed
    def set_killed(task: db.Task):
        for run in task.runs:
            if RunStatus.has_finished(run.status):
                continue  # don't overwrite status if run is already finished
            run.status = RunStatus.KILLED.value
            run.finished_at = dt.datetime.now(dt.timezone.utc)
            run.save()

    set_killed(task)
    for subtask in task.children:
        set_killed(subtask)
