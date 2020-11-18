# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
import logging

from flask_restful import Resource, abort
from flasgger import swag_from
from pathlib import Path
from flask_principal import Permission

from vantage6.server.resource import with_user
from vantage6.common import logger_name
from vantage6.server.permission import (
    register_rule, valid_rule_need
)
from vantage6.server.model.rule import Operation, Scope

from vantage6.server._version import __version__

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Version,
        path,
        endpoint='version',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Version(Resource):

    @swag_from(str(Path(r"swagger/version.yaml")), endpoint='version')
    def get(self):
        """Return the version of this server."""

        return {"version": __version__}
