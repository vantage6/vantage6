# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/collaboration'
"""
import os, os.path

from flask import g, request
from flask_restful import Resource, abort
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

from requests import codes as rqc

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

from . import parse_datetime
from . import with_user_or_client, with_client
from ._schema import *


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(Result,
        path,
        path + '/<int:id>',
        endpoint='result'
    )


# Schemas
result_schema = ResultSchema()
result_inc_schema = ResultTaskIncludedSchema()

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Result(Resource):
    """Resource for /api/task"""

    @with_user_or_client
    def get(self, id=None):
        if id:
            t = db.TaskResult.get(id)
        else:
            session = db.Session()
            q = session.query(db.TaskResult)

            if request.args.get('state') == 'open':
                q = q.filter(db.TaskResult.finished_at == None)

            if request.args.get('client_id'):
                q = q.filter_by(client_id=request.args.get('client_id'))                

            t = q.all()

        if request.args.get('include') == 'task':
            s = result_inc_schema
        else:
            s = result_schema

        return s.dump(t, many=not bool(id))


    def post(self, id=None):
        abort(rqc.not_allowed, message="Results cannot be created by POSTing.")


    @with_client
    def put(self, id):
        """Update a Result."""
        data = request.get_json()
        result = db.TaskResult.get(id)

        if result.client_id != g.client.id:
            abort(rqc.forbidden, message="Unauthorized: this is not your result to PUT!")

        if result.finished_at is not None:
            abort(rqc.not_allowed, message="Cannot update a finished result!")            

        result.started_at = parse_datetime(data.get("started_at"), result.started_at)
        result.finished_at = parse_datetime(data.get("finished_at"))
        result.result = data.get("result")
        result.log = data.get("log")

        result.save()

        return result


