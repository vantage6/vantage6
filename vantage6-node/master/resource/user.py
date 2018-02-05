# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/user'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import db

from . import with_user_or_client, with_user

def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = os.path.join(API_BASE, module_name)
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(User,
        path,
        path + '/<int:user_id>',
    )

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class User(Resource):

    @with_user
    def get(self, user_id=None):
        """Return user details."""
        return db.User.get(user_id)


    @with_user
    def post(self):
        """Create a new User."""
        # FIXME: implement!
        pass

