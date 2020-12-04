# -*- coding: utf-8 -*-
import datetime
import logging

from functools import wraps

from flask import g, request
from flask_restful import Resource
from flask_jwt_extended import (
    get_jwt_claims, get_jwt_identity, jwt_required
)

from vantage6.common import logger_name
from vantage6.server import db

log = logging.getLogger(logger_name(__name__))


class ServicesResources(Resource):

    def __init__(self, socketio, mail, api, permissions):
        self.socketio = socketio
        self.mail = mail
        self.api = api
        self.permissions = permissions


# ------------------------------------------------------------------------------
# Helper functions/decoraters ...
# ------------------------------------------------------------------------------
def only_for(types=['user', 'node', 'container']):
    """JWT endpoint protection decorator"""
    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):

            # decode JWT-token
            identity = get_jwt_identity()
            claims = get_jwt_claims()

            # check that identity has access to endpoint
            g.type = claims["type"]
            # log.debug(f"Endpoint accessed as {g.type}")

            if g.type not in types:
                msg = f"{g.type}'s are not allowed to access {request.url} " \
                      f"({request.method})"
                log.warning(msg)
                raise Exception(msg)

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
