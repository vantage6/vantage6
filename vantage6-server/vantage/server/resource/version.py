# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
from __future__ import print_function, unicode_literals

import logging

from flask_restful import Resource, abort
from flasgger import swag_from
from pathlib import Path

from vantage import constants

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db
# from .. import __version__


def setup(api, API_BASE):

    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(
        Version,
        path,
        endpoint='version',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Version(Resource):

    @swag_from(str(Path(r"swagger/version.yaml")), endpoint='version')
    def get(self):
        """Return the version of this server."""
        
        return {"version": constants.VERSION}