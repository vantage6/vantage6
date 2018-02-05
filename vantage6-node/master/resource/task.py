# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
import os, os.path

from flask import g, request
from flask_restful import Resource, abort
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity


import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import db

from . import parse_datetime
from . import with_user_or_client, with_client
from ._schema import *


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = os.path.join(API_BASE, module_name)
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(Task,
        path,
        path + '/<int:id>',
        endpoint='task'        
    )
    api.add_resource(TaskResult,
        path + '/<int:id>/result',
        path + '/<int:id>/result/<int:result_id>',
    )


# Schemas
task_schema = TaskSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    @jwt_required
    def get(self, id=None):
        t = db.Task.get(id)
        return task_schema.dump(t, many=not bool(id))


    @jwt_required
    def post(self):
        """Create a new Task."""
        abort(400, message="Please post new tasks to /api/collaboration/<id>/task")


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    @jwt_required
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        return task.results

    @with_client
    def post(self, id, result_id):
        """Update an oustanding result for task."""
        data = request.get_json()
        result = db.TaskResult.get(result_id)

        if result.id != id:
            abort(401, message="Result is not part of task!")

        if result.client_id != g.client.id:
            abort(401, message="Unauthorized: this is not your result to post!")

        if result.finished_at is not None:
            abort(401, message="Cannot update a finished result!")            

        result.started_at = parse_datetime(data.get("started_at"), result.started_at)
        result.finished_at = parse_datetime(data.get("finished_at"))
        result.result = data.get("result")
        result.log = data.get("log")

        result.save()

        return result
