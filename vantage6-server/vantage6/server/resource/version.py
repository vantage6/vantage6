# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
from __future__ import print_function, unicode_literals

import logging

from flask_restful import Resource, abort
from flasgger import swag_from
from pathlib import Path

from vantage6.server.permission import register_rule
from vantage6.server._version import __version__



module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

def setup(api, API_BASE):

    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Version,
        path,
        endpoint='version',
        methods=('GET',)
    )

from flask_principal import Permission, RoleNeed, Need
from vantage6.server.resource import with_user

test_permission = Permission(RoleNeed("root"))
test_permission.description = "Testing the principal package!"


register_rule("see version", [], "GET", "Can you see the version or not?")



# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------

class Version(Resource):

    # @with_user
    @test_permission.require(http_exception=403)
    @swag_from(str(Path(r"swagger/version.yaml")), endpoint='version')
    def get(self):
        """Return the version of this server."""

        return {"version": __version__}