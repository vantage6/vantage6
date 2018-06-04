# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

from requests import codes as rqc

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

from . import with_user_or_node
from ._schema import *


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(Collaboration,
        path,
        path + '/<int:id>',
        endpoint='collaboration'
    )
    api.add_resource(CollaborationOrganization,
        path+'/<int:id>/organization',
        path+'/<int:id>/organization/<int:organization_id>'
    )
    api.add_resource(CollaborationNode,
        path+'/<int:id>/node',
        path+'/<int:id>/node/<int:node_id>',
    )
    api.add_resource(CollaborationTask, 
        path+'/<int:id>/task',
        path+'/<int:id>/task/<int:task_id>',
    )


# Schemas
collaboration_schema = CollaborationSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Collaboration(Resource):

    @jwt_required
    def get(self, id=None):
        """Return either a single collaboration or a list of all available collaborations."""
        c = db.Collaboration.get(id)
        return collaboration_schema.dump(c, many=not id)


    @jwt_required
    def post(self):
        """Create a new organization."""
        data = request.get_json()
        collaboration = db.Collaboration.fromDict(data)
        collaboration.save()

        return collaboration


    @jwt_required
    def put(self, id):
        """Update an organization."""
        pass


class CollaborationOrganization(Resource):
    """Resource for /api/collaboration/<int:id>/organization."""

    @jwt_required
    def get(self, id):
        """Return organizations for a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        return collaboration.organizations

    @jwt_required
    def post(self, id):
        """Add an organizations to a specific collaboration."""
        data = request.get_json()
        collaboration = db.Collaboration.get(id)
        organization = db.Organization.get(data['id'])
        collaboration.organizations.append(organization)
        collaboration.save()
        return collaboration.organizations


class CollaborationNode(Resource):
    """Resource for /api/collaboration/<int:id>/node."""

    @jwt_required
    def get(self, id):
        collaboration = db.Collaboration.get(id)
        return collaboration.nodes

    @jwt_required
    def post(self, id):
        """Add an organizations to a specific collaboration."""
        data = request.get_json()
        collaboration = db.Collaboration.get(id)
        node = db.Node.get(data['id'])
        collaboration.nodes.append(node)
        collaboration.save()
        return collaboration.nodes


class CollaborationTask(Resource):
    """Resource for /api/collaboration/<int:id>/task."""

    @jwt_required
    def get(self, id, task_id=None):
        if task_id is not None:
            t = db.Task.get(task_id)
            return task_schema.dump(t)

        collaboration = db.Collaboration.get(id)
        return tasks_schema.dump(collaboration.tasks)

    @jwt_required
    def post(self, id):
        """Add a task to a specific collaboration."""
        abort(rqc.bad_request, "Please POST to /api/task instead.")

        # collaboration = db.Collaboration.get(id)
        # data = request.get_json()
        
        # task = db.Task(collaboration=collaboration)
        # task.name = data.get('name', '')
        # task.description = data.get('description', '')
        # task.image = data.get('image', '')
        # task.input = data.get('input', '')
        # task.status = "open"

        # for c in collaboration.nodes:
        #     result = db.TaskResult(task=task, node=c)

        # task.save()
        # return task




