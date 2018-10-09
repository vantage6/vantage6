# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/node'
"""

import logging
import uuid

from flask import g, request
from flask_restful import Resource, reqparse
from http import HTTPStatus
from flasgger.utils import swag_from
from . import with_user_or_node, with_user
from pathlib import Path

from ._schema import *

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base):
    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Node,
        path,
        endpoint='node_without_node_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Node,
        path + '/<int:id>',
        endpoint='node_with_node_id',
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

    @with_user
    @swag_from(Path("swagger\get_node_with_node_id.yaml"), endpoint='node_with_node_id')
    @swag_from(Path("swagger\get_node_without_node_id.yaml"), endpoint='node_without_node_id')
    def get(self, id=None):
        nodes = db.Node.get(id)

        if id:
            if not nodes:
                return {"msg": "node with id={} not found".format(id)}, HTTPStatus.NOT_FOUND  # 404
            if nodes.organization_id != g.user.organization_id and g.user.roles != 'admin':
                return {"msg": "you are not allowed to see this node"}, HTTPStatus.FORBIDDEN  # 403
        else:
            # only the nodes of the users organization are returned
            if g.user.roles != 'admin':
                nodes = [node for node in nodes if node.organization_id == g.user.organization_id]

        return self.node_schema.dump(nodes, many=not id).data, HTTPStatus.OK  # 200

    @with_user
    @swag_from(Path("swagger\post_node_without_node_id.yaml"), endpoint='node_without_node_id')
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
    @swag_from(Path("swagger\delete_node_with_node_id.yaml"), endpoint='node_with_node_id')
    def delete(self, id):
        """delete node account"""
        node = db.Node.get(id)

        if not node:
            return {"msg": "node with id={} not found".format(id)}, HTTPStatus.NOT_FOUND  # 404

        if node.organization_id != g.user.organization_id and g.user.roles != 'admin':
            return {"msg": "you are not allowed to delete this node"}, HTTPStatus.FORBIDDEN  # 403

        node.delete()

        return {"msg": "successfully deleted node id={}".format(id)}, HTTPStatus.OK  # 200

    @with_user
    @swag_from(Path("swagger\patch_node_with_node_id.yaml"), endpoint='node_with_node_id')
    def patch(self, id):
        """update existing node"""
        parser = reqparse.RequestParser()
        parser.add_argument(
            'collaboration_id',
            type=int,
            required=True,
            help="This field cannot be left blank!"
        )
        data = parser.parse_args()

        node = db.Node.get(id)

        # create new node
        if not node:
            collaboration = db.Collaboration.get(data['collaboration_id'])

            # check that the collaboration exists
            if not collaboration:
                return {"msg": "collaboration_id '{}' does not exist".format(
                    data['collaboration_id'])}, HTTPStatus.NOT_FOUND  # 404

            # new api-key which node can use to authenticate
            api_key = str(uuid.uuid1())

            # store the new node
            # TODO an admin does not have to belong to an organization?
            organization = g.user.organization
            node = db.Node(
                id=id,
                name="{} - {} Node".format(organization.name, collaboration.name),
                collaboration=collaboration,
                organization=organization,
                api_key=api_key
            )
            node.save()
        else:  # update node
            if node.organization_id != g.user.organization_id and g.user.roles != 'admin':
                return {"msg": "you are not allowed to edit this node"}, HTTPStatus.FORBIDDEN  # 403

            node.collaboration_id = data['collaboration_id']
            node.save()

        return self.node_schema.dump(node).data, HTTPStatus.OK  # 200


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
    @swag_from(Path("swagger\get_node_tasks.yaml"), endpoint='node_tasks')
    def get(self, id):
        """Return a list of tasks for a node or a single task <task_result_id> belonging t.

        If the query parameter 'state' equals 'open' the list is
        filtered to return only tasks without result.
        """

        # get tasks that belong to node <id>
        node = db.Node.get(id)
        if not node:
            return {"msg": "node with id={} not found".format(id)}, HTTPStatus.NOT_FOUND  # 404

        # filter tasks if a specific state is requested
        if request.args.get('state') == 'open':
            results = [result for result in node.taskresults if not result.finished_at]
            return self.task_result_schema.dump(results, many=True), HTTPStatus.OK  # 200

        results = [result for result in node.taskresults]
        return results, HTTPStatus.OK  # 200
