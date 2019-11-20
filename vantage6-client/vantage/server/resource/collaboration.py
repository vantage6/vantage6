# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""

from __future__ import print_function, unicode_literals

import json
import logging

from flask import request, g
from flask_restful import Resource, reqparse
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage.server import db
from vantage.server.resource._schema import CollaborationSchema, TaskSchema
from vantage.server.resource import with_user_or_node, with_user, only_for

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):
    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Collaboration,
        path,
        endpoint='collaboration_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Collaboration,
        path + '/<int:id>',
        endpoint='collaboration_with_id',
        methods=('GET', 'PATCH', 'DELETE')
    )
    api.add_resource(
        CollaborationOrganization,
        path+'/<int:id>/organization',
        endpoint='collaboration_with_id_organization',
        methods=('GET', 'POST', 'DELETE')
    )
    api.add_resource(
        CollaborationNode,
        path+'/<int:id>/node',
        endpoint='collaboration_with_id_node',
        methods=('GET', 'POST', 'DELETE')
    )
    api.add_resource(
        CollaborationTask,
        path+'/<int:id>/task',
        endpoint='collaboration_with_id_task',
        methods=('GET', 'POST', 'DELETE')
    )


# Schemas
collaboration_schema = CollaborationSchema()
tasks_schema = TaskSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Collaboration(Resource):

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_without_id.yaml")), endpoint='collaboration_without_id')
    def post(self):
        """create a new collaboration"""

        parser = reqparse.RequestParser()
        parser.add_argument(
            'name',
            type=str,
            required=True,
            help="This field cannot be left blank!"
        )
        parser.add_argument(
            'organization_ids',
            type=int,
            required=True,
            action='append'
        )
        parser.add_argument(
            'encrypted',
            type=int,
            required=False
        )
        data = parser.parse_args()

        encrypted = True if data["encrypted"] == 1 else False
            
        collaboration = db.Collaboration(
            name=data['name'],
            organizations=[
                db.Organization.get(org_id) for org_id in data['organization_ids'] if db.Organization.get(org_id)
            ],
            encrypted=encrypted
        )

        collaboration.save()
        return collaboration_schema.dump(collaboration).data, HTTPStatus.OK

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_collaboration_with_id.yaml")), endpoint='collaboration_with_id')
    @swag_from(str(Path(r"swagger/get_collaboration_without_id.yaml")), endpoint='collaboration_without_id')
    def get(self, id=None):
        """collaboration or list of collaborations in case no id is provided"""
        collaboration = db.Collaboration.get(id)

        # check that collaboration exists
        if not collaboration:
            return {"msg": "collaboration having id={} not found".format(id)}, HTTPStatus.NOT_FOUND  # 404

        # check if node or user have permission to view the collaboration
        # organization_ids = collaboration.get_organization_ids()
        # auth = g.user if g.user is not None else g.node
        # if auth.organization_id not in organization_ids and "admin" not in g.user.roles:
        #     log.warning("user or node from organization_id={} tries to access collaboration_id={}".format(
        #         auth.organization_id, id)
        #     )
        #     return {"msg": "you do not have permission to view this collaboration"}

        return collaboration_schema.dump(collaboration, many=not id).data, HTTPStatus.OK  # 200

    @with_user
    @swag_from(str(Path(r"swagger/patch_collaboration_with_id.yaml")), endpoint='collaboration_with_id')
    def patch(self, id):
        """update a collaboration"""
        # if "admin" not in g.user.roles:
        #     return {"msg": "only administrators can edit collaborations"}, 403  # forbidden

        collaboration = db.Collaboration.get(id)

        # check if collaboration exists
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND  # 404

        # only update fields that are provided
        data = request.get_json()
        if "name" in data:
            collaboration.name = data["name"]
        if "organization_ids" in data:
            collaboration.organizations = [
                db.Organization.get(org_id) for org_id in data['organization_ids'] if db.Organization.get(org_id)
            ]
        collaboration.save()

        return collaboration_schema.dump(collaboration, many=False), HTTPStatus.OK  # 200

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_with_id.yaml")), endpoint='collaboration_with_id')
    def delete(self, id):
        """delete collaboration"""

        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration id={} is not found".format(id)}, 404

        collaboration.delete()
        return {"msg": "node id={} successfully deleted".format(id)}, 200


class CollaborationOrganization(Resource):
    """Resource for /api/collaboration/<int:id>/organization."""

    @only_for(["node","user","container"])
    @swag_from(str(Path(r"swagger/get_collaboration_organization.yaml")), endpoint='collaboration_with_id_organization')
    def get(self, id):
        """Return organizations for a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        # only users that belong to the collaboration can view collaborators
        # organization_ids = collaboration.get_organization_ids()
        # if g.user.organization_id not in organization_ids and "admin" not in g.user.roles:
        #     return {"msg": "only users that belong to this collaboration can view its organizations"}, 403

        return collaboration.organizations, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_organization.yaml")), endpoint='collaboration_with_id_organization')
    def post(self, id):
        """Add an organizations to a specific collaboration."""
        # get collaboration to which te organization should be added
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        # get the organization
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": "organization with id={} is not found"}, HTTPStatus.NOT_FOUND

        # append organization to the collaboration
        collaboration.organizations.append(organization)
        collaboration.save()
        return collaboration.organizations

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_organization.yaml")), endpoint='collaboration_with_id_organization')
    def delete(self, id):
        """Removes an organization from a collaboration."""
        # get collaboration from which organization should be removed
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        # get organization which should be deleted
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": "organization with id={} is not found"}, HTTPStatus.NOT_FOUND

        # delete organization and update
        collaboration.organizations.remove(organization)
        collaboration.save()
        return {"msg": "organization id={} successfully deleted from collaboration id={}".format(
            data['id'], id
        )}, HTTPStatus.OK


class CollaborationNode(Resource):
    """Resource for /api/collaboration/<int:id>/node."""

    @with_user
    @swag_from(str(Path(r"swagger/get_collaboration_node.yaml")), endpoint='collaboration_with_id_node')
    def get(self, id):
        """"Return a list of nodes that belong to the collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        return collaboration.nodes, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_node.yaml")), endpoint='collaboration_with_id_node')
    def post(self, id):
        """Add an node to a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        data = request.get_json()
        node = db.Node.get(data['id'])
        if not node:
            return {"msg": "node id={} not found"}, HTTPStatus.NOT_FOUND
        if node in collaboration.nodes:
            return {"msg": "node id={} is already in collaboration id={}".format(
                data['id'], id
            )}, HTTPStatus.BAD_REQUEST

        collaboration.nodes.append(node)
        collaboration.save()
        return collaboration.nodes

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_node.yaml")), endpoint='collaboration_with_id_node')
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
    @swag_from(str(Path(r"swagger/get_collaboration_task.yaml")), endpoint='collaboration_with_id_task')
    def get(self, id):
        """List of tasks that belong to a collaboration"""
        collaboration = db.Collaboration.get(id)
        return tasks_schema.dump(collaboration.tasks, many=True)

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_task.yaml")), endpoint='collaboration_with_id_task')
    def post(self, id):
        """Attach new task to collaboration"""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        data = request.get_json()
        task = db.Task(
            collaboration=collaboration,
            name=data.get('name', ''),
            description=data.get('description', ''),
            image=data.get('image', ''),
            input=data.get('input', '') if isinstance(data.get('input', ''), str) else json.dumps(data.get('input')),
        )
        task.save()

        for organization in collaboration.organizations:
            result = db.Result(
                task=task,
                organization=organization
            )
            result.save()

        return tasks_schema.dump(collaboration.tasks, many=True)

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_task.yaml")), endpoint='collaboration_with_id_task')
    def delete(self, id):
        """Remove task from collaboration"""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": "collaboration having collaboration_id={} can not be found".format(
                id
            )}, HTTPStatus.NOT_FOUND

        data = request.get_json()
        task_id = data['task_id']
        task = db.Task.get(task_id)
        if not task:
            return {"msg": "Task id={} not found".format(task_id)}, HTTPStatus.NOT_FOUND
        if task_id not in collaboration.get_task_ids():
            return {"msg": "Task id={} is not part of collaboration id={}".format(task_id, id)}, HTTPStatus.BAD_REQUEST
        task.delete()
        return {"msg": "Task id={} is removed from collaboration id={}".format(task_id, id)}, HTTPStatus.OK
