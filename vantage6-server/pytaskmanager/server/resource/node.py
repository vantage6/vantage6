# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/node'
"""
import os, os.path

from flask import g, request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims

import datetime
import logging

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

from . import with_user_or_node
from ._schema import *


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(Node,
        path,
        path + '/<int:id>',
        endpoint='node'
    )
    api.add_resource(NodeTasks,
        path + '/<int:id>/task',
        path + '/<int:id>/task/<int:taskresult_id>',
    )


# Schemas
node_schema = NodeSchema()
taskresult_schema = TaskResultSchema()

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Node(Resource):
    """Resource for /api/node/<int:id>."""

    @with_user_or_node
    def get(self, id=None):
        node = db.Node.get(id)

        if g.user:
            if id:
                # FIXME: use proper roles instead of CSV
                if 'root' in g.user.roles.replace(' ', '').split() or g.user in node.organization.users:
                    # json_representation = db.jsonable(node)
                    # json_representation['api_key'] = node.api_key
                    # return json_representation
                    return node_schema.dump(node)

        elif g.node:
            log.info(g.node)

        # return db.Node.get(id)
        return node_schema.dump(node, many=not id)


class NodeTasks(Resource):
    """Resource for /api/node/<int:id>/task."""

    @with_user_or_node
    def get(self, id, taskresult_id=None):
        """Return a list of tasks for a node.

        If the query parameter 'state' equals 'open' the list is
        filtered to return only tasks without result.
        """
        log = logging.getLogger(__name__)


        if taskresult_id is not None:
            result = db.TaskResult.get(taskresult_id)
            return taskresult_schema.dump(result)

        # If taskresult_id is None, we're returning all taskresults
        # that belong to this node (potentially filtered by state).
        node = db.Node.get(id)

        if request.args.get('state') == 'open':
            results = [result for result in node.taskresults if result.finished_at is None]
            return taskresult_schema.dump(results, many=True)

        return [result for result in node.taskresults]



