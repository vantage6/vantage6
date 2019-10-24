# -*- coding: utf-8 -*-
"""
Resources ... 
"""
import datetime
import logging
import os
import os.path
import sys

from functools import wraps

from flask import g, request
from flask_jwt_extended import get_jwt_claims, get_jwt_identity, jwt_required

from vantage.server import db

log = logging.getLogger(__name__.split('.')[-1])

# ------------------------------------------------------------------------------
# Helpfer functions/decoraters ... 
# ------------------------------------------------------------------------------
def only_for(types = ['user', 'node', 'container']):
    """JWT endpoint protection decorator"""
    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):

            # decode JWT-token
            identity = get_jwt_identity()
            claims = get_jwt_claims()

            # check that identity has access to endpoint            
            g.type = claims["type"]
            log.debug(f"Endpoint accessed as {g.type}")
            if g.type not in types:
                log.warning(f"Illegal attempt from {g.type} to access endpoint")
                raise Exception(f"{g.type}'s are not allowed!")

            # do some specific stuff per identity
            g.user = g.container = g.node = None
            if g.type == 'user':
                user = get_and_update_authenticatable_info(identity)
                g.user = user
                assert g.user.type == g.type
            elif g.type == 'node':
                node = get_and_update_authenticatable_info(identity)
                g.node = node
                assert g.node.type == g.type
            elif g.type == 'container':
                g.container = identity
            else:
                raise Exception(f"Unknown entity: {g.type}")

            return fn(*args, **kwargs)
        return jwt_required(decorator)
    return protection_decorator

def get_and_update_authenticatable_info(auth_id):
    """Get DB entity from ID and update info."""
    auth = db.Authenticatable.get(auth_id)
    auth.last_seen = datetime.datetime.utcnow()
    auth.ip = request.remote_addr
    auth.save()
    return auth

# create alias decorators
with_user_or_node = only_for(["user", "node"])
with_user = only_for(["user"])
with_node = only_for(["node"])
with_container = only_for(["container"])

def parse_datetime(dt=None, default=None):
    if dt:
        return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')
    return default
