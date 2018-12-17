# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/task'
"""
import logging
import json

from flask import g, request, url_for
from flask_restful import Resource
from . import with_user_or_node, with_user, only_for
from ._schema import TaskSchema, TaskIncludedSchema
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

from pytaskmanager.server import db
from pytaskmanager.server import socketio

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Task,
        path,
        endpoint='task_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Task,
        path + '/<int:id>',
        endpoint='task_with_id',
        methods=('GET', 'DELETE')
    )
    api.add_resource(
        TaskResult,
        path + '/<int:id>/result',
        endpoint='task_result',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    task_schema = TaskSchema()
    task_result_schema = TaskIncludedSchema()

    @only_for(["user", "node"])
    @swag_from(str(Path(r"swagger/get_task_with_id.yaml")), endpoint='task_with_id')
    @swag_from(str(Path(r"swagger/get_task_without_id.yaml")), endpoint='task_without_id')
    def get(self, id=None):
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} is not found"}, HTTPStatus.NOT_FOUND

        s = self.task_result_schema if request.args.get('include') == 'results' else self.task_schema
        return s.dump(task, many=not id).data, HTTPStatus.OK

    @only_for(["user", "container"])
    @swag_from(str(Path(r"swagger/post_task_without_id.yaml")), endpoint='task_without_id')
    def post(self):
        """Create a new Task."""
        #TODO split container/node into sepperate endpoints.. 
        if not request.is_json:
            return {"msg": "No JSON body found..."}, HTTPStatus.BAD_REQUEST
        data = request.get_json()

        collaboration_id = data.get('collaboration_id', None)
        collaboration = db.Collaboration.get(collaboration_id, None)
        if not collaboration:
            return {"msg": f"collaboration id={collaboration_id} not found"},\
            HTTPStatus.NOT_FOUND

        # create new task
        task = db.Task(
            collaboration=collaboration,
            name=data.get('name', ''),
            description=data.get('description', ''),
            image=data.get('image', ''),
            database=data.get('database', '')
        )

        
        if g.user:# a user is considered to be the seed of the task

            task.run_id = task.next_run_id()
            log.debug(f"New run_id {task.run_id}")
        
        elif g.container: # in case of a container we have to be extra carefull
            if g.container["image"] != task.image:
                msg = f"Container from node={g.container['node_id']} attempts to post a task using illegal image={task.image}"
                log.warning(msg)

                msg = f"You do not have permission to use image={task.image}"
                return {"msg": msg,HTTPStatus.UNAUTHORIZED}

            # check master task is not completed yet
            if db.Task.get(g.container["task_id"]).complete:
                msg = f"Container from node={g.container['node_id']} attempts to start sub-task for a completed task={g.container['task_id']}"
                log.warning(msg)

                msg = f"Master task={g.container['task_id']} is already completed"
                return {"msg": msg, HTTPStatus.BAD_REQUEST}

            # # check that node id is indeed part of the collaboration
            if not g.container["collaboration_id"] == collaboration_id:
                log.warning(f"Container attempts to create a task outside its collaboration!")
                return {"msg": f"You cannot create tasks in collaboration_id={collaboration_id}"},\
                    HTTPStatus.BAD_REQUEST
            
            # container tasks are always sub-tasks
            task.parent_task_id = g.container["task_id"]
            task.run_id = db.Task.get(g.container["task_id"]).run_id
            log.debug(f"Sub task from parent_task_id={task.parent_task_id}")

        # TODO check that organization of the user is in the collaboration!

        input_ = data.get('input', '')
        if not isinstance(input_, str):
            input_ = json.dumps(input_)

        task.input = input_
        task.status = "open"
        task.save()

        log.info(f"New task created for collaboration '{task.collaboration.name}'")
        if g.type == 'user':
            log.debug(f" created by: '{g.user.username}'")
        else:
            log.debug((f" created by container on node_id={g.container['node_id']}"
                       f" for (master) task_id={g.container['task_id']}"))
        log.debug(f" url: '{url_for('task_with_id', id=task.id)}'")
        log.debug(f" name: '{task.name}'")
        log.debug(f" image: '{task.image}'")
        log.debug(f"Assigning task to {len(collaboration.nodes)} nodes")


        # a collaboration can include multiple nodes
        for c in collaboration.nodes:
            log.debug(f"   Assigning task to '{c.name}'")
            db.TaskResult(task=task, node=c)

        task.save()

        # if the node is connected send a socket message that there
        # is a new task available
        socketio.emit(
            'new_task', 
            task.id, 
            room='collaboration_'+str(task.collaboration_id),
            namespace='/tasks'
        )

        return self.task_schema.dump(task, many=False)

    @only_for(['user'])
    @swag_from(str(Path(r"swagger/delete_task_with_id.yaml")), endpoint='task_with_id')
    def delete(self, id):
        """Deletes a task"""
        # TODO we might want to delete the corresponding results also?

        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        task.delete()
        return {"msg": "task id={} successfully deleted".format(id)}, HTTPStatus.OK


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    @only_for(['user', 'container'])
    @swag_from(str(Path(r"swagger/get_task_result.yaml")), endpoint='task_result')
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        return task.results, HTTPStatus.OK

