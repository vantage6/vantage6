# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource, reqparse
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

from requests import codes as rqc

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

from pytaskmanager.server.resource import with_user_or_node, with_user
from ._schema import *


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Collaboration,
        path,
        path + '/<int:id>',
        endpoint='collaboration'
    )
    api.add_resource(
        CollaborationOrganization,
        path+'/<int:id>/organization',
        path+'/<int:id>/organization/<int:organization_id>'
    )
    api.add_resource(
        CollaborationNode,
        path+'/<int:id>/node',
        path+'/<int:id>/node/<int:node_id>',
    )
    api.add_resource(
        CollaborationTask,
        path+'/<int:id>/task',
        path+'/<int:id>/task/<int:task_id>',
    )


# Schemas
collaboration_schema = CollaborationSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Collaboration(Resource):

    @with_user
    def post(self, id=None):
        """create a new collaboration"""
        if id:
            return {"msg": "id provided, but this is not allowed for the POST method"}, 400

        data = request.get_json()

        collaboration = db.Collaboration(
            name=data['name'],
            organizations=[
                db.Organization.get(org_id) for org_id in data['organization_ids'] if db.Organization.get(org_id)
            ]
        )

        return collaboration_schema.dump(collaboration).data

    @with_user_or_node
    def get(self, id=None):
        """collaboration or list of collaborations in case no id is provided"""
        # TODO only the collaboration to which the node or user belongs should be shown
        collaboration = db.Collaboration.get(id)
        return collaboration_schema.dump(collaboration, many=not id).data

    # @with_user
    # def put(self, id=None):
    #     """update a collaboration"""
    #     data = request.get_json()
    #
    #     if not id:
    #         return {"msg": "to create or update a node you need to specify an id"}, 400
    #
    #     collaboration = db.Collaboration.get(id)
    #
    #     if not collaboration:
    #         collaboration = db.Collaboration(id=id)
    #
    #     if "name" in data:
    #         collaboration.name = data["name"]
    #     if "organization_ids" in data:
    #         collaboration.organizations = [
    #             db.Organization.get(org_id) for org_id in data['organization_ids'] if db.Organization.get(org_id)
    #         ]
    #     collaboration.save()
    #
    #     return collaboration, 200

    @with_user
    def delete(self, id=None):
        """123"""
        if not id:
            return {"msg": "to delete a node you need to specify an id"}, 400

        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration id={} is not found".format(id)}

        collaboration.delete()
        return {"msg": "node id={} successfully deleted".format(id)}, 200


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




