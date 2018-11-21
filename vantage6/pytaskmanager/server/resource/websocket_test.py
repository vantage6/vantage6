# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/websocket_test'
"""
from __future__ import print_function, unicode_literals

import logging

from flask_restful import Resource, abort
from flask_socketio import send
from flasgger import swag_from
from pathlib import Path

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db
from .. import socketio


def setup(api, API_BASE):

    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(
        Test,
        path,
        endpoint='test',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Test(Resource):

    @swag_from(str(Path(r"swagger/websocket-test.yaml")), endpoint='websocket_test')
    def get(self):
        """Return something."""
        socketio.send("you're welcome!", room='all_nodes')
        return socketio.server.manager.rooms
