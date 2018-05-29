# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
from __future__ import print_function, unicode_literals
import os, os.path


from flask import request
from flask_restful import Resource, abort
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db
# from .. import __version__

def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = '/'.join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(Version, path)

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Version(Resource):

    def get(self):
        """Return the version of this server."""
        return {"version": "0.1dev1"}