# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask import request, g

from vantage6.common import logger_name
from vantage6.server.resource import ServicesResources, with_user
from vantage6.server import db

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


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class KillTask(ServicesResources):
    """ Provide endpoint to kill all containers executing a certain task """
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, "task")

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
          |Task|Global|Delete|❌|❌|Delete any task|\n
          |Task|Organization|Delete|✅|✅|Delete any task in your organization|
          \n

          Accessible to users with permission to delete tasks.

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
        if not self.r.d_glo.can():
            orgs = task.collaboration.organizations
            if not (self.r.d_org.can() and g.user.organization in orgs):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        kill_list = [{
            'task_id': id_,
            'result_id': r.id,
            'organization_id': r.organization_id
        } for r in task.results]
        self.socketio.emit(
            'kill_containers', {
                'kill_list': kill_list,
                'collaboration_id': task.collaboration.id
            }, namespace='/tasks'
        )

        # TODO ensure child tasks are also killed

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
          |Task|Global|Delete|❌|❌|Delete any task|\n
          |Task|Organization|Delete|✅|✅|Delete any task in your organization|
          \n

          Accessible to users with permission to delete tasks.

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
        if not self.r.d_glo.can():
            orgs = node.collaboration.organizations
            if not (self.r.d_org.can() and g.user.organization in orgs):
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
