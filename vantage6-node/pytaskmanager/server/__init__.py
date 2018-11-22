#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import importlib

from flask import Flask, Response, request, render_template, make_response, g, session
from flask_restful import Resource, Api, fields
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, get_jwt_claims, get_raw_jwt, jwt_required, jwt_optional, verify_jwt_in_request

from flask_marshmallow import Marshmallow
from flask_socketio import SocketIO, emit, send,join_room, leave_room


from flasgger import Swagger

import datetime
import logging

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import json

from . import db
from pytaskmanager import util
from pytaskmanager import APPNAME
from pytaskmanager.server.websockets import DefaultSocketNamespace


# ------------------------------------------------------------------------------
# Initialize Flask
# ------------------------------------------------------------------------------
RESOURCES_INITIALIZED = False
API_BASE = '/api'
WEB_BASE = '/app'

# Create Flask app
app = Flask(APPNAME)
# TODO app.config
app.config['JWT_AUTH_URL_RULE'] ='/api/token'

template = {
    "components":{
        "securitySchemes":{
            "bearerAuth":{
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": " JWT"
            }
        }
    },
    "security": [
        {"bearerAuth": []}
    ]
}

app.config['SWAGGER'] = {
    'title': 'PyTaskManager',
    'uiversion': 3,
    'openapi': '3.0.0',
}
swagger = Swagger(app, template=template)

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
    return db.Authenticatable.get(identity)


# ------------------------------------------------------------------------------
# Setup flask-socketio
# ------------------------------------------------------------------------------
try:
    socketio = SocketIO(app, async_mode='gevent_uwsgi')
except:
    socketio = SocketIO(app)

socketio.on_namespace(DefaultSocketNamespace("/"))


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
    return """
    <html>
        <head>
        <script type="text/javascript" src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/2.1.1/socket.io.dev.js"></script>
        <script type="text/javascript" charset="utf-8">
            setTimeout(function() {
                console.log('running javascript');
                socket = io.connect('http://' + document.domain + ':' + location.port, { transports: ['websocket']});

                socket.on('message', function(msg){
                    console.log(msg);
                });

                socket.on('connect', function() {
                    console.log('emitting!');
                    socket.emit("my event", {data: "I'm connected!"});
                });},
                2000
            );
        </script>
        </head>
        <body>
            <h1>Hi there!!</h2>
        </body>
    </html>
"""


# ------------------------------------------------------------------------------
# init & run
# ------------------------------------------------------------------------------
def init(environment=None, init_resources_=False):
    """Initialize the server using a site-wide ServerContext."""
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    if environment is None:
        if 'environment' in os.environ:
            environment = os.environ['environment']
        else:
            environment = 'prod'

    # Load configuration and initialize logging system
    ctx = util.ServerContext(APPNAME, 'default')
    ctx.init(ctx.config_file, environment)

    if init_resources_:
        init_resources(ctx)

    uri = ctx.get_database_location()
    print('-' * 80)
    print(uri)
    print('-' * 80)
    db.init(uri)


def init_resources(ctx):
    # Load resources
    global RESOURCES_INITIALIZED

    if RESOURCES_INITIALIZED:
        return

    api_base = ctx.config['env']['api_path']

    resources = [
            'node',
            'collaboration',
            'organization',
            'task',
            'result',
            'token',
            'user',
            'version',
            'websocket_test',
    ]

    # Load resources
    load_resources(api, api_base, resources)

    # Make sure we do this only once
    RESOURCES_INITIALIZED = True


def run(ctx, *args, **kwargs):
    """Run the server.

        Note that this method is never called when the server is instantiated
        through the Web Server Gateway Interface (WSGI)!
    """
    # Prevent logging from urllib3
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Set an extra long expiration time on access tokens for testing
    if ctx.config['env']['type'] == 'test':
        log.warning("Setting 'JWT_ACCESS_TOKEN_EXPIRES' to one day!")
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

    # Actually start the server
    # app.run(*args, **kwargs)
    socketio.run(app, *args, **kwargs)



