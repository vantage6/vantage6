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

from vantage6.server.resource import ServicesResources

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db
from .. import socketio


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Test,
        path,
        endpoint='test',
        methods=('GET',),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Test(ServicesResources):

    @swag_from(str(Path(r"swagger/websocket-test.yaml")), endpoint='websocket_test')
    def get(self):
        """Return something."""
        socketio.send("you're welcome!", room='all_nodes')
        return socketio.server.manager.rooms
