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
def with_user_or_client(fn):

    def decorator(*args, **kwargs):
        user_or_client_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_client_id: {}'.format(user_or_client_id))
        # log.info(claims)
        user_or_client = db.Authenticatable.get(user_or_client_id)
        user_or_client.last_seen = datetime.datetime.utcnow()
        user_or_client.ip = request.remote_addr
        user_or_client.save()

        g.type = user_or_client.type

        if g.type == 'user':
            g.user = user_or_client
            g.client = None
        elif g.type == 'client':
            g.client = user_or_client
            g.user = None
        else:
            raise Exception('Unknown user/client type!?')

        return fn(*args, **kwargs)

    return jwt_required(decorator)


def with_user(fn):

    def decorator(*args, **kwargs):
        user_or_client_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_client_id: {}'.format(user_or_client_id))
        # log.info(claims)

        user_or_client = db.Authenticatable.get(user_or_client_id)
        user_or_client.last_seen = datetime.datetime.utcnow()
        user_or_client.ip = request.remote_addr
        user_or_client.save()

        g.type = user_or_client.type

        if g.type == 'user':
            g.user = user_or_client
        else:
            raise Exception("Not authenticated as user!?")

        return fn(*args, **kwargs)

    return jwt_required(decorator)


def with_client(fn):

    def decorator(*args, **kwargs):
        user_or_client_id = get_jwt_identity()
        claims = get_jwt_claims()

        # log.info('decorator - user_or_client_id: {}'.format(user_or_client_id))
        # log.info(claims)

        user_or_client = db.Authenticatable.get(user_or_client_id)
        user_or_client.last_seen = datetime.datetime.utcnow()
        user_or_client.ip = request.remote_addr
        user_or_client.save()

        g.type = user_or_client.type

        if g.type == 'client':
            g.client = user_or_client
        else:
            raise Exception("Not authenticated as client!?")

        return fn(*args, **kwargs)

    return jwt_required(decorator)



def parse_datetime(dt=None, default=None):
    if dt:
        return datetime.datetime.strptime(dt, '%Y-%m-%dT%H:%M:%S.%f')

    return default




