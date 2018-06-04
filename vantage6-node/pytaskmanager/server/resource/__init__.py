# -*- coding: utf-8 -*-
"""
Resources ... 
"""
import sys
import os, os.path

from flask import g, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt_claims

import datetime
import logging
log = logging.getLogger(__name__)

from .. import db



# ------------------------------------------------------------------------------
# Helpfer functions/decoraters ... 
# ------------------------------------------------------------------------------
def with_user_or_node(fn):

    def decorator(*args, **kwargs):
        user_or_node_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_node_id: {}'.format(user_or_node_id))
        # log.info(claims)
        user_or_node = db.Authenticatable.get(user_or_node_id)
        user_or_node.last_seen = datetime.datetime.utcnow()
        user_or_node.ip = request.remote_addr
        user_or_node.save()

        g.type = user_or_node.type

        if g.type == 'user':
            g.user = user_or_node
            g.node = None
        elif g.type == 'node':
            g.node = user_or_node
            g.user = None
        else:
            raise Exception('Unknown user/node type!?')

        return fn(*args, **kwargs)

    return jwt_required(decorator)


def with_user(fn):

    def decorator(*args, **kwargs):
        user_or_node_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_node_id: {}'.format(user_or_node_id))
        # log.info(claims)

        user_or_node = db.Authenticatable.get(user_or_node_id)
        user_or_node.last_seen = datetime.datetime.utcnow()
        user_or_node.ip = request.remote_addr
        user_or_node.save()

        g.type = user_or_node.type

        if g.type == 'user':
            g.user = user_or_node
        else:
            raise Exception("Not authenticated as user!?")

        return fn(*args, **kwargs)

    return jwt_required(decorator)


def with_node(fn):

    def decorator(*args, **kwargs):
        user_or_node_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_node_id: {}'.format(user_or_node_id))
        # log.info(claims)

        user_or_node = db.Authenticatable.get(user_or_node_id)
        user_or_node.last_seen = datetime.datetime.utcnow()
        user_or_node.ip = request.remote_addr
        user_or_node.save()

        g.type = user_or_node.type

        if g.type == 'node':
            g.node = user_or_node
        else:
            raise Exception("Not authenticated as node!?")

        return fn(*args, **kwargs)

    return jwt_required(decorator)



def parse_datetime(dt=None, default=None):
    if dt:
        return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')

    return default




