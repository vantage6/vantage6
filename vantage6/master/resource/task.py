# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
import os, os.path

from flask import g, request
from flask_restful import Resource, abort

from requests import codes as rqc

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
task_inc_schema = TaskIncludedSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Task(Resource):
    """Resource for /api/task"""

    @with_user_or_client
    def get(self, id=None):
        t = db.Task.get(id)

        if request.args.get('include') == 'results':
            s = task_inc_schema
        else:
            s = task_schema

        return s.dump(t, many=not bool(id))


    def post(self):
        """Create a new Task."""
        abort(rqc.not_allowed, message="Please post new tasks to /api/collaboration/<id>/task")


class TaskResult(Resource):
    """Resource for /api/task/<int:id>/result"""

    @with_user_or_client
    def get(self, id):
        """Return results for task."""
        task = db.Task.get(id)
        return task.results

