# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
import logging
import json

from flask import g, request
from flask_restful import Resource
from . import with_user_or_node, with_user
from ._schema import TaskSchema, TaskIncludedSchema
from http import HTTPStatus
from flasgger import swag_from

from pytaskmanager.server import db

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Task,
        path,
        endpoint='task_without_id'
    )
    api.add_resource(
        Task,
        path + '/<int:id>',
        endpoint='task_with_id'
    )
    api.add_resource(
        TaskResult,
        path + '/<int:id>/result',
        endpoint='task_result'
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    task_schema = TaskSchema()
    task_result_schema = TaskIncludedSchema()

    @with_user_or_node
    @swag_from("swagger/get_task_with_id.yaml", endpoint='task_with_id')
    @swag_from("swagger/get_task_without_id.yaml", endpoint='task_without_id')
    def get(self, id=None):
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} is not found"}, HTTPStatus.NOT_FOUND

        s = self.task_result_schema if request.args.get('include') == 'results' else self.task_schema
        return s.dump(task, many=not id), HTTPStatus.OK

    @with_user
    @swag_from("swagger/post_task_without_id.yaml", endpoint='task_without_id')
    def post(self):
        """Create a new Task."""
        data = request.get_json()
        collaboration_id = data.get('collaboration_id')
        if not collaboration_id:
            log.error("JSON causing the error:\n{}".format(data))
            return {"msg": "JSON should contain 'collaboration_id'"}, HTTPStatus.BAD_REQUEST

        collaboration = db.Collaboration.get(collaboration_id)
        if not collaboration:
            return {"msg": "collaboration id={} not found".format(collaboration_id)}, HTTPStatus.NOT_FOUND

        task = db.Task(collaboration=collaboration)
        task.name = data.get('name', '')
        task.description = data.get('description', '')
        task.image = data.get('image', '')

        input_ = data.get('input', '')
        if not isinstance(input_, str):
            input_ = json.dumps(input_)

        task.input = input_
        task.status = "open"

        # a collaboration can include multiple nodes
        for c in collaboration.nodes:
            db.TaskResult(task=task, node=c)

        task.save()
        return self.task_schema.dump(task, many=False)

    # @with_user_or_node
    # def patch(self, id=None):
    #     # TODO not sure if this is such a good idea?
    #     if not id:
    #         return {"msg": "no task id is specified"}, HTTPStatus.BAD_REQUEST
    #
    #     task = db.Task.get(id)
    #     if not task:
    #         return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND
    #
    #     data = request.get_json()
    #     if 'name' in data:
    #         task.name = data['name']
    #     if 'description' in data:
    #         task.description = data['description']
    #     if 'image' in data:
    #         task.image = data['image']
    #     if 'status' in data:
    #         task.status = data['status']
    #     if 'input' in data:
    #         input_ = data['input']
    #         if not isinstance(input_, str):
    #             input_ = json.dumps(input_)
    #         task.input = input_

    @with_user
    @swag_from("swagger/delete_task_with_id.yaml", endpoint='task_with_id')
    def delete(self, id=None):
        """Deletes a task"""
        # TODO we might want to delete the corresponding results also?
        # if not id:
        #     return {"msg": "no task id is specified"}, HTTPStatus.BAD_REQUEST

        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        task.delete()
        return {"msg": "task id={} successfully deleted".format(id)}, HTTPStatus.OK


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    @with_user_or_node
    @swag_from("swagger/get_task_result.yaml", endpoint='task_result')
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        if not task:
            return {"msg": "task id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        return task.results, HTTPStatus.OK

