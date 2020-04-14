# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/node'
"""

import logging
import uuid

import json

from flask import g, request
from flask_restful import Resource, reqparse
from http import HTTPStatus
from flasgger.utils import swag_from
from . import with_user_or_node, with_user
from pathlib import Path


from vantage6.server.model.base import Database

from ._schema import *

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):
    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Node,
        path,
        endpoint='node_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Node,
        path + '/<int:id>',
        endpoint='node_with_id',
        methods=('GET', 'DELETE', 'PATCH')
    )
    api.add_resource(
        NodeTasks,
        path + '/<int:id>/task',
        endpoint='node_tasks',
        methods=('GET', )
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------

class Node(Resource):

    # Schemas
    node_schema = NodeSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_node_with_id.yaml")),
        endpoint='node_with_id')
    @swag_from(str(Path(r"swagger/get_node_without_id.yaml")),
        endpoint='node_without_id')
    def get(self, id=None):
        results = db.Node.get(id)
        user_or_node = g.user or g.node

        is_root = False

        # Only users can be root, not containers.
        if g.user:
            is_root = g.user.username == 'root'

        if id:
            if not results:
                msg = {"msg": f"Couldn't find node {id}"}
                return msg, HTTPStatus.NOT_FOUND

            if is_root:
                # Let's not make a fuss ...
                return self.node_schema.dump(results, many=False)

            if (results.organization_id != user_or_node.organization_id) \
                    and 'admin' not in g.user.roles:
                msg = {"msg": "you are not allowed to see this node"}
                return msg, HTTPStatus.FORBIDDEN  # 403

        else:
            if not is_root:
                # only the results of the user's organization are returned
                org_id = g.user.organization_id
                results = [n for n in results if n.organization_id == org_id]

        return self.node_schema.dump(results, many=not id).data, HTTPStatus.OK  # 200

    @with_user
    @swag_from(str(Path(r"swagger/post_node_without_node_id.yaml")), endpoint='node_without_id')
    def post(self):

        parser = reqparse.RequestParser()
        parser.add_argument(
            "collaboration_id",
            type=int,
            required=True,
            help="This field cannot be left blank!"
        )
        data = parser.parse_args()

        collaboration = db.Collaboration.get(data["collaboration_id"])

        # check that the collaboration exists
        if not collaboration:
            return {"msg": "collaboration_id '{}' does not exist".format(
                data["collaboration_id"]
            )}, HTTPStatus.NOT_FOUND  # 404

        # new api-key which node can use to authenticate
        api_key = str(uuid.uuid1())

        # store the new node
        # TODO an admin does not have to belong to an organization?
        # TODO we need to check that the organization belongs to the collaboration
        organization = g.user.organization
        node = db.Node(
            name="{} - {} Node".format(organization.name, collaboration.name),
            collaboration=collaboration,
            organization=organization,
            api_key=api_key
        )
        node.save()

        return self.node_schema.dump(node).data, HTTPStatus.CREATED  # 201

    @with_user
    @swag_from(str(Path(r"swagger/delete_node_with_id.yaml")), endpoint='node_with_id')
    def delete(self, id):
        """delete node account"""
        node = db.Node.get(id)

        if not node:
            return {"msg": "node with id={} not found".format(id)}, HTTPStatus.NOT_FOUND  # 404

        if node.organization_id != g.user.organization_id and g.user.roles != 'admin':
            return {"msg": "you are not allowed to delete this node"}, HTTPStatus.FORBIDDEN  # 403

        node.delete()

        return {"msg": "successfully deleted node id={}".format(id)}, HTTPStatus.OK  # 200

    @with_user_or_node
    @swag_from(str(Path(r"swagger/patch_node_with_id.yaml")), endpoint='node_with_id')
    def patch(self, id):
        """update existing node"""
        node = db.Node.get(id)

        # do not create new nodes here
        if not node:
            return {"msg": "Use POST to create a new node"}, HTTPStatus.FORBIDDEN  # 403

        data = request.get_json()
        if 'state' in data:
            data['state'] = json.dumps(data['state'])

        if g.node:
            if g.node.id == node.id:
                log.debug("Hey! It's me! I got this!")
                node.update(include=['status', 'state'], **data)
            else:
                log.debug("This doesn't seem right! You don't look like me!?")
                return {"msg": "you are not allowed to edit this node"}, HTTPStatus.FORBIDDEN  # 403

        if g.user:
            is_root = g.user.roles == 'root'

            if is_root:
                # root can do everything ... he's really cool
                log.debug('root is making changes!')
                node.update(**data)
                node.save()

            else:
                # Ok, so we're not root ...
                incorrect_organization = node.organization_id != g.user.organization_id
                incorrect_role = g.user.roles != 'admin'

                if (incorrect_organization or incorrect_role):
                    return {"msg": "you are not allowed to edit this node"}, HTTPStatus.FORBIDDEN  # 403

                # We've established you're an admin for your organisation. Feel free
                # to make some changes to the api_key, name or status.
                allowed_attrs = ['name', 'api_key', 'status', 'state']
                node.update(include=allowed_attrs, **data)
                node.save()

        return self.node_schema.dump(node)  # 200


class NodeTasks(Resource):
    """Resource for /api/node/<int:id>/task.
    returns task(s) belonging to a specific node

       Resource for /api/node/<int:id>/task/<int:id>
    returns


    TODO do we need the second usage? we can retrieve tasks by the endpoint /api/task
    TODO if we do want to keep this, we need to make sure the user only sees task that belong to this node
    TODO also the user can only see nodes which belong to their organization
    """

    task_result_schema = TaskResultSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_node_tasks.yaml")), endpoint='node_tasks')
    def get(self, id):
        """Return a list of tasks for a node or a single task <task_result_id> belonging t.

        If the query parameter 'state' equals 'open' the list is
        filtered to return only tasks without result.
        """
        # get tasks that belong to node <id>
        node = db.Node.get(id)
        if not node:
            return {"msg": "node with id={} not found".format(id)}, \
                HTTPStatus.NOT_FOUND  # 404

        # select tasks from organization that are within the collaboration
        # of the node
        results = []
        for result in node.organization.results:

            if node.collaboration == result.task.collaboration:
                # result belongs to node
                if request.args.get('state') == 'open':
                    if result.complete:
                        results.append(result)
                else:
                    results.append(result)

        return self.task_result_schema.dump(results, many=True), \
            HTTPStatus.OK  # 200