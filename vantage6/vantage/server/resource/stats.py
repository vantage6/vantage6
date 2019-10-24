# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/stats'
"""
import logging
import json

import flask
from flask import g, request, url_for
from flask_restful import Resource
from . import with_user_or_node, with_user, only_for
from ._schema import *
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

import psutil

from vantage.server import db
from vantage.server import socketio

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Stats,
        path,
        endpoint='stats',
        methods=('GET', )
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Stats(Resource):
    """Resource for /api/stats"""

    # stats_schema = StatsSchema()
    @only_for(["user", "node"])
    def get(self, id=None):
        schema = CollaborationSchemaSimple(many=True)

        return {
            'collaborations': schema.dump(db.Collaboration.get()).data
        }


    

