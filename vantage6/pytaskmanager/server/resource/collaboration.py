# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""

from __future__ import print_function, unicode_literals

import json
import logging

from flask import request, g
from flask_restful import Resource, reqparse

from pytaskmanager.server import db
from pytaskmanager.server.resource._schema import CollaborationSchema, TaskSchema
from pytaskmanager.server.resource import with_user_or_node, with_user

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
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
        path+'/<int:id>/organization'
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
tasks_schema = TaskSchema()


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

        collaboration.save()
        return collaboration_schema.dump(collaboration).data

    @with_user_or_node
    def get(self, id=None):
        """collaboration or list of collaborations in case no id is provided"""
        collaboration = db.Collaboration.get(id)

        # check that collaboration exists
        if not collaboration:
            return {"msg": "collaboration having id={} not found".format(id)}, 404

        # check if node or user have permission to view the collaboration
        # organization_ids = collaboration.get_organization_ids()
        # auth = g.user if g.user is not None else g.node
        # if auth.organization_id not in organization_ids and "admin" not in g.user.roles:
        #     log.warning("user or node from organization_id={} tries to access collaboration_id={}".format(
        #         auth.organization_id, id)
        #     )
        #     return {"msg": "you do not have permission to view this collaboration"}

        return collaboration_schema.dump(collaboration, many=not id).data

    @with_user
    def patch(self, organization_id=None):
        """update a collaboration"""
        # if "admin" not in g.user.roles:
        #     return {"msg": "only administrators can edit collaborations"}, 403  # forbidden
        if not organization_id:
            return {"msg": "to create or update a node you need to specify an organization_id"}, 400  # bad request

        collaboration = db.Collaboration.get(organization_id)
        # check if collaboration exists
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                organization_id
            )}, 404  # not found

        # only update fields that are provided
        data = request.get_json()
        if "name" in data:
            collaboration.name = data["name"]
        if "organization_ids" in data:
            collaboration.organizations = [
                db.Organization.get(org_id) for org_id in data['organization_ids'] if db.Organization.get(org_id)
            ]
        collaboration.save()

        return collaboration_schema.dump(collaboration, many=False), 200

    @with_user
    def delete(self, id=None):
        """123"""
        if not id:
            return {"msg": "to delete a node you need to specify an id"}, 400

        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration id={} is not found".format(id)}, 404

        collaboration.delete()
        return {"msg": "node id={} successfully deleted".format(id)}, 200


class CollaborationOrganization(Resource):
    """Resource for /api/collaboration/<int:id>/organization."""

    @with_user
    def get(self, id=None):
        """Return organizations for a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        # only users that belong to the collaboration can view collaborators
        # organization_ids = collaboration.get_organization_ids()
        # if g.user.organization_id not in organization_ids and "admin" not in g.user.roles:
        #     return {"msg": "only users that belong to this collaboration can view its organizations"}, 403

        return collaboration.organizations

    @with_user
    def post(self, id=None):
        """Add an organizations to a specific collaboration."""
        # get collaboration to which te organization should be added
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        # get the organization
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": "organization with id={} is not found"}, 404

        # append organization to the collaboration
        collaboration.organizations.append(organization)
        collaboration.save()
        return collaboration.organizations

    @with_user
    def delete(self, id=None):
        """Removes an organization from a collaboration."""
        # get collaboration from which organization should be removed
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        # get organization which should be deleted
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": "organization with id={} is not found"}, 404

        # delete organization and update
        collaboration.organizations.remove(organization)
        collaboration.save()
        return {"msg": "organization id={} successfully deleted from collaboration id={}".format(data['id'], id)}, 200


class CollaborationNode(Resource):
    """Resource for /api/collaboration/<int:id>/node."""

    @with_user
    def get(self, id):
        """"Return a list of nodes that belong to the collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        return collaboration.nodes

    @with_user
    def post(self, id):
        """Add an node to a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        data = request.get_json()
        node = db.Node.get(data['id'])
        if not node:
            return {"msg": "node id={} not found"}, 404
        if node in collaboration.nodes:
            return {"msg": "node id={} is already in collaboration id={}".format(data['id'], id)}, 400

        collaboration.nodes.append(node)
        collaboration.save()
        return collaboration.nodes

    @with_user
    def delete(self, id):
        """Remove node from collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        data = request.get_json()
        node = db.Node.get(data['id'])
        if not node:
            return {"msg": "node id={} not found"}, 404
        if node not in collaboration.nodes:
            return {"msg": "node id={} is not part of collaboration id={}".format(data['id'], id)}, 400

        collaboration.nodes.remove(node)
        return {"msg": "node id={} removed from collaboration id={}".format(data['id'], id)}, 200


class CollaborationTask(Resource):
    """Resource for /api/collaboration/<int:id>/task."""

    @with_user_or_node
    def get(self, id, task_id=None):
        """List of tasks that belong to a collaboration"""
        if task_id is not None:
            t = db.Task.get(task_id)
            return tasks_schema.dump(t)

        collaboration = db.Collaboration.get(id)
        return tasks_schema.dump(collaboration.tasks, many=True)

    @with_user
    def post(self, id):
        """Attach new task to collaboration"""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        data = request.get_json()
        task = db.Task(
            collaboration=collaboration,
            name=data.get('name', ''),
            description=data.get('description', ''),
            image=data.get('image', ''),
            input=data.get('input', '') if isinstance(data.get('input', ''), str) else json.dumps(data.get('input')),
            status="open"
        )

        for node in collaboration.nodes:
            db.TaskResult(task=task, node=node)

        task.save()
        return tasks_schema.dump(collaboration.tasks, many=True)

    @with_user
    def delete(self, id):
        """Remove task from collaboration"""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, 404

        data = request.get_json()
        task_id = data['task_id']
        task = db.Task.get(task_id)
        if not task:
            return {"msg": "Task id={} not found".format(task_id)}, 404
        if task_id not in collaboration.get_task_ids():
            return {"msg": "Task id={} is not part of collaboration id={}".format(task_id, id)}, 400
        task.delete()
        return {"msg": "Task id={} is removed from collaboration id={}".format(task_id, id)}, 200
