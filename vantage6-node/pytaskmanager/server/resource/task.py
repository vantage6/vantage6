# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
import logging
import json

from flask import g, request
from flask_restful import Resource, abort
from requests import codes as rqc
from . import with_user_or_node
from ._schema import TaskSchema, TaskIncludedSchema
from pytaskmanager.server import db

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(
        Task,
        path,
        path + '/<int:id>',
        endpoint='task'        
    )
    api.add_resource(
        TaskResult,
        path + '/<int:id>/result',
        path + '/<int:id>/result/<int:result_id>',
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    @with_user_or_node
    def get(self, id=None):
        t = db.Task.get(id)

        if request.args.get('include') == 'results':
            s = TaskIncludedSchema()
        else:
            s = TaskSchema()

        return s.dump(t, many=not bool(id))

    @with_user_or_node
    def post(self):
        """Create a new Task."""
        data = request.get_json()
        collaboration_id = data.get('collaboration_id')

        if not collaboration_id:
            log.error("JSON causing the error:\n{}".format(data))
            abort(rqc.bad_request, "JSON should contain 'collaboration_id'")

        collaboration = db.Collaboration.get(collaboration_id)
        
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
            result = db.TaskResult(task=task, node=c)

        task.save()
        return TaskSchema().dump(task, many=False)


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    @with_user_or_node
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        return task.results

