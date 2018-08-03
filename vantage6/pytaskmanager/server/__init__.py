#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import importlib

from flask import Flask, Response, request, render_template, make_response
from flask_restful import Resource, Api, fields
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_claims

from flask_marshmallow import Marshmallow
from flasgger import Swagger

import datetime
import logging

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import json

from . import db
from pytaskmanager import util


# ------------------------------------------------------------------------------
# Initialize Flask
# ------------------------------------------------------------------------------
RESOURCES_INITIALIZED = False
API_BASE = '/api'
WEB_BASE = '/app'

# Create Flask app
app = Flask('taskmaster')
# TODO app.config
app.config['JWT_AUTH_URL_RULE'] ='/api/token'

app.config['SWAGGER'] = {
    'title': 'PyTaskManager',
    'uiversion': 3,
    'openapi': '3.0.0',
    'definitions': {
        'Collaboration':{
            'properties':{
                'collaboration_id':{
                    'type': 'integer'
                }
            }
        },
        'User':{
            'properties':{
                'username':{
                    'type': 'string'
                },
                'password':{
                    'type': 'string'
                }
            },
            'example':{
                'username': 'string',
                'password': 'string'
            }
        },
        'Node':{
            'properties':{
                'api_key':{
                    'type': 'string'
                }
            }
        }
    },
    "securityDefinitions": { "api_key": { "type": "apiKey", "name": "Authorization", "in": "header" }}
    # 'securityDefinitions': {
    #     'bearerAuth': {
    #         'type': 'http',
    #         'scheme': 'bearer',
    #         'bearerFormat': 'JWT'
    #     }
    # }
}
swagger = Swagger(app)

# swagger.load_swagger_file('D:/Repositories/PyTaskManager/pytaskmanager/server/swagger/components.yaml')


# Enable cross-origin resource sharing
CORS(app)


# ------------------------------------------------------------------------------
# Api - REST JSON-rpc
# ------------------------------------------------------------------------------
api = Api(app)


@api.representation('application/json')
def output_json(data, code, headers=None):

    if isinstance(data, db.Base):
        data = db.jsonable(data)
    elif isinstance(data, list) and len(data) and isinstance(data[0], db.Base):
        data = db.jsonable(data)

    resp = make_response(json.dumps(data), code)
    resp.headers.extend(headers or {})
    return resp


# ------------------------------------------------------------------------------
# Setup SQLAlchemy and Marshmallow for marshalling/serializing
# ------------------------------------------------------------------------------
ma = Marshmallow(app)


# ------------------------------------------------------------------------------
# Setup the Flask-JWT-Extended extension (JWT: JSON Web Token)
# ------------------------------------------------------------------------------
app.config['JWT_SECRET_KEY'] = 'f8a87430-fe18-11e7-a7b2-a45e60d00d91'
jwt = JWTManager(app)


@jwt.user_claims_loader
def user_claims_loader(user_or_node):
    if isinstance(user_or_node, db.User):
        type_ = 'user'
        roles = user_or_node.roles.split(',')
    else:
        type_ = 'node'
        roles = []
    
    claims = {
        'type': type_,
        'roles': roles,
    }

    return claims


@jwt.user_identity_loader
def user_identity_loader(user_or_node):
    if isinstance(user_or_node, db.Authenticatable):
        return user_or_node.id
    
    msg = "Could not create a JSON serializable identity from '{}'"
    msg = msg.format(user_or_node)
    log.error(msg)
    return None


@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    # user_or_node = None
    # claims = get_jwt_claims()

    return db.Authenticatable.get(identity)


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
def load_resources(api, API_BASE, resources):
    """Import the modules containing Resources."""
    for name in resources:
        module = importlib.import_module('pytaskmanager.server.resource.' + name)
        module.setup(api, API_BASE)


# ------------------------------------------------------------------------------
# Http routes
# ------------------------------------------------------------------------------
@app.route(WEB_BASE+'/', defaults={'path': ''})
@app.route(WEB_BASE+'/<path:path>')
def index(path):
    return "Hello, World"


# ------------------------------------------------------------------------------
# init & run
# ------------------------------------------------------------------------------
def init_resources(ctx):
    # Load resources
    global RESOURCES_INITIALIZED

    if RESOURCES_INITIALIZED:
        return

    api_base = ctx.config['app']['api_path']

    resources = [
            'node',
            'collaboration',
            'organization',
            'task',
            'result',
            'token',
            'user',
            'version',
    ]

    # Load resources
    load_resources(api, api_base, resources)

    # Make sure we do this only once
    RESOURCES_INITIALIZED = True


def run(ctx, *args, **kwargs):
    # Load configuration and init logging
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    uri = ctx.get_database_location()
    db.init(uri)
    
    # Set an extra long expiration time on access tokens for testing
    if ctx.config['env']['type'] == 'test':
        log.warning("Setting 'JWT_ACCESS_TOKEN_EXPIRES' to one day!")
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

    # Actually start the server
    app.run(*args, **kwargs)



