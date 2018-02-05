# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/client'
"""
import os, os.path

from flask import g, request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims

import datetime
import logging

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import db

from . import with_user_or_client
from ._schema import *


def setup(api, API_BASE):
    path = os.path.join(API_BASE, module_name)
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(Client, 
        path,
        path + '/<int:id>',
        endpoint='client'
    )
    api.add_resource(ClientTasks,
        path + '/<int:id>/task',
        path + '/<int:id>/task/<int:taskresult_id>',
    )


# Schemas
client_schema = ClientSchema()
taskresult_schema = TaskResultSchema()

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Client(Resource):
    """Resource for /api/client/<int:id>."""

    @with_user_or_client
    def get(self, id=None):
        client = db.Client.get(id)

        if g.user:
            log.info(g.user)
            
            if id:
                # FIXME: use proper roles instead of CSV
                if 'root' in g.user.roles.replace(' ', '').split() or g.user in client.organization.users:
                    # json_representation = db.jsonable(client)
                    # json_representation['api_key'] = client.api_key
                    # return json_representation
                    return client_schema.dump(client)

        elif g.client:
            log.info(g.client)

        # return db.Client.get(id)
        return client_schema.dump(client, many=not id)


class ClientTasks(Resource):
    """Resource for /api/client/<int:id>/task."""

    @with_user_or_client
    def get(self, id, taskresult_id=None):
        """Return a list of tasks for a client.

        If the query parameter 'state' equals 'open' the list is
        filtered to return only tasks without result.
        """
        log = logging.getLogger(__name__)


        if taskresult_id is not None:
            result = db.TaskResult.get(taskresult_id)
            return taskresult_schema.dump(result)

        # If taskresult_id is None, we're returning all taskresults
        # that belong to this client (potentially filtered by state).
        client = db.Client.get(id)

        if request.args.get('state') == 'open':
            results = [result for result in client.taskresults if result.finished_at is None]
            return taskresult_schema.dump(results, many=True)

        return [result for result in client.taskresults]



