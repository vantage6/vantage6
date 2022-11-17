# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask import request, g

from vantage6.common import logger_name
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server import db
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        KillTask,
        path+'/task',
        endpoint='kill_task',
        methods=('POST',),
        resource_class_kwargs=services
    )

    api.add_resource(
        KillNodeTasks,
        path+'/node/tasks',
        endpoint='kill_node_tasks',
        methods=('POST',),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):

    # TODO in v4, change the operations below to 'SEND' and 'RECEIVE' as these
    # are permissions to do stuff via socket connections
    add = permissions.appender(module_name)

    add(scope=S.ORGANIZATION, operation=P.VIEW,
        description="view websocket events of your organization")
    add(scope=S.COLLABORATION, operation=P.VIEW,
        description="view websocket events of your collaborations")
    add(scope=S.GLOBAL, operation=P.VIEW,
        description="view websocket events")
    add(scope=S.ORGANIZATION, operation=P.CREATE,
        description="send websocket events for your organization")
    add(scope=S.COLLABORATION, operation=P.CREATE,
        description="send websocket events for your collaborations")
    add(scope=S.GLOBAL, operation=P.CREATE,
        description="send websocket events to all collaborations")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class KillTask(ServicesResources):
    """ Provide endpoint to kill all containers executing a certain task """

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
          |Event|Collaboration|Create|✅|✅|
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
            description: Task not found
          401:
            description: Unauthorized
          400:
            description: No task id provided

        tags: ["Kill tasks"]
        """
        # obtain task id or node id from request
        body = request.get_json()
        id_ = body.get("id")
        if not id_:
            return {"msg": "No task id provided!"}, HTTPStatus.BAD_REQUEST

        task = db.Task.get(id_)
        if not task:
            return {"msg": f"Task id={id_} not found"}, HTTPStatus.NOT_FOUND

        # Check permissions. If someone doesn't have global permissions, we
        # check if their organization is part of the appropriate collaboration.
        if not self.r.c_glo.can():
            orgs = task.collaboration.organizations
            if not (self.r.c_org.can() and g.user.organization in orgs):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # Gather results and task ids of current task and child tasks
        child_results = [r for child in task.children for r in child.results]
        all_results = task.results + child_results
        child_task_ids = [child.id for child in task.children]
        all_task_ids = [id_] + child_task_ids

        kill_list = [{
            'task_id': task_id,
            'result_id': result.id,
            'organization_id': result.organization_id
        } for result, task_id in zip(all_results, all_task_ids)]

        # emit socket event to the node to execute the container kills
        self.socketio.emit(
            'kill_containers', {
                'kill_list': kill_list,
                'collaboration_id': task.collaboration.id
            }, namespace='/tasks'
        )

        return {
            "msg": "Nodes have been instructed to kill any containers running "
                   f"for task {id_}."
        }, HTTPStatus.OK


class KillNodeTasks(ServicesResources):
    """ Provide endpoint to kill all tasks on a certain node """
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, "task")

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
          |Event|Collaboration|Delete|✅|✅|Create kill signal for all tasks
          on any node in collaborations|\n
          |Event|Organization|Delete|✅|✅|Create kill signal for all tasks on
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
            description: No task id provided

        tags: ["Kill tasks"]
        """
        # obtain task id or node id from request
        body = request.get_json()
        id_ = body.get("id")
        if not id_:
            return {"msg": "No node id provided!"}, HTTPStatus.BAD_REQUEST

        node = db.Node.get(id_)
        if not node:
            return {"msg": f"Node id={id_} not found"}, HTTPStatus.NOT_FOUND

        # Check permissions. If someone doesn't have global permissions, we
        # check if their organization is part of the appropriate collaboration.
        if not self.r.c_glo.can():
            collab_orgs = node.collaboration.organizations
            if not (
                (self.r.c_col.can() and g.user.organization in collab_orgs) or
                (self.r.c_org.can() and
                    node.organization_id == g.user.organization_id)
            ):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        self.socketio.emit(
            'kill_containers', {
                'node_id': node.id,
                'collaboration_id': node.collaboration_id
            }, namespace='/tasks'
        )

        return {
            "msg": f"Node {node.id} has been instructed to kill all containers"
                   " running on it."
        }, HTTPStatus.OK
