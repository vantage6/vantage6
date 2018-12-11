#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import importlib

try:
    # Stuff needed for running shell in a browser
    import pty
    import select
    import subprocess
    import struct
    import fcntl
    import termios
except: 
    pass

from flask import Flask, Response, request, render_template, make_response, g, session
from flask_restful import Resource, Api, fields
from flask_cors import CORS
from flask_jwt_extended import JWTManager, get_jwt_identity, get_jwt_claims, get_raw_jwt, jwt_required, jwt_optional, verify_jwt_in_request

from flask_marshmallow import Marshmallow
from flask_socketio import SocketIO, emit, send,join_room, leave_room
import flask_socketio



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

# '#/components/schemas/Pet'
template = {
    "components":{
        "securitySchemes":{
            "bearerAuth":{
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": " JWT"
            }
        },
        "schemas":{
            "Task":{
                "properties":{
                    "description":{
                        "type": "string"
                    },
                    "image":{
                        "type": "string",
                    },
                    "input":{
                        "type": "string"
                    },
                    "name":{
                        "type": "string"
                    }
                },
                "required": [
                    "image"
                ]
            },
            "Collaboration": {
                "properties": {
                    "collaboration_id": {
                        "type": "integer"
                    }
                },
                "example":{
                    "collaboration_id": 1
                }
            },
            "Node": {
                "properties": {
                    "api_key": {
                        "type": "string"
                    }
                }
            },
            "User": {
                "example": {
                    "password": "secret!", 
                    "username": "yourname"
                }, 
                "properties": {
                    "password": {"type": "string"}, 
                    "username": {"type": "string"}
                }
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

# socketio.on_namespace(DefaultSocketNamespace("/"))
socketio.on_namespace(DefaultSocketNamespace("/tasks"))


def start_interpreter():
    # create child process attached to a pty we can read from and write to
    env = app.config['environment']
    cmd = ['ipython', '-m', 'pytaskmanager.server.shell', '-i', '--', env]

    master_fd, slave_fd = pty.openpty()
    child = subprocess.Popen(
        cmd, 
        stdin=slave_fd, 
        stdout=slave_fd, 
        stderr=slave_fd
    )
    app.config["child"] = child
    app.config["fd"] = master_fd
    app.config["master_fd"] = master_fd
    app.config["slave_fd"] = slave_fd

    set_winsize(master_fd, 50, 50)

    socketio.start_background_task(target=read_and_forward_pty_output)
    print("ipython terminal backend")


def assert_running_interpreter(start_if_required=False):

    try:
        if app.config["child"].poll() is None:
            return True
    except KeyError:
        pass


    if start_if_required:
        start_interpreter()
        return True

    else:
        if not 'socket_connections' in app.config:
            print('This is weird!')
            app.config['socket_connections'] = []

        nr_clients = len(app.config['socket_connections'])

        print('-' * 80)
        print("The interpreter has been shut down.")
        print("It will be restarted when a client reconnects.")
        print()
        if nr_clients == 1:
            print(f'There is 1 client connected')
        else:
            print(f'There are {nr_clients} clients connected')
        print('disconnecting ...')

        for sid in app.config['socket_connections']:
            with app.app_context():
                print(f' - {sid}')
                flask_socketio.disconnect(sid=sid, namespace='/pty')

        print('-' * 80)

        return False


def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def read_and_forward_pty_output():
    max_read_bytes = 1024 * 20

    fd = app.config["fd"]
    timeout_sec = 0.01

    while assert_running_interpreter():
        socketio.sleep(timeout_sec)

        (rs, ws, es) = select.select([fd], [], [], timeout_sec)

        for r in rs:
            output = os.read(r, max_read_bytes).decode()
            socketio.emit("pty-output", {"output": output}, namespace="/pty")


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    """write to the child pty. The pty sees this as if you are typing in a real
    terminal.
    """
    if assert_running_interpreter():
        raw_data = data["input"].encode()
        os.write(app.config["fd"], raw_data)


@socketio.on("resize", namespace="/pty")
def resize(data):
    if assert_running_interpreter():
        set_winsize(app.config["fd"], data["rows"], data["cols"])


@socketio.on("connect", namespace="/pty")
def connect():
    """new client connected"""
    environment = app.config['environment']

    print('-' * 80)
    print('connect /pty')
    print('environment: {environment}')
    print('-' * 80)

    try:
        verify_jwt_in_request()
    except Exception as e:
        log.error("Could not connect client! No or Invalid JWT token?")
        log.info(list(request.headers.keys()))
        log.exception(e)
    else:
        # At this point we're sure that the user/client/whatever 
        # checks out
        user_or_node_id = get_jwt_identity()
        auth = db.Authenticatable.get(user_or_node_id)

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        log.info(f'Client identified as <{session.type}>: <{session.name}>')

        assert_running_interpreter(start_if_required=True)

        if not 'socket_connections' in app.config:
            app.config['socket_connections'] = []

        print(f'connecting {request.sid}')
        app.config['socket_connections'].append(request.sid)
        return True

    return False

@socketio.on("disconnect", namespace="/pty")
def disconnect():
    print(f'Client {request.sid} disconnected')
    app.config['socket_connections'].remove(request.sid)


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
# @app.route(WEB_BASE+'/<path:path>')
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
# def init(environment=None, init_resources_=False):
#     """Initialize the server using a site-wide ServerContext."""
#     logging.getLogger("urllib3").setLevel(logging.WARNING)

#     if environment is None:
#         if 'environment' in os.environ:
#             environment = os.environ['environment']
#         else:
#             environment = 'prod'

#     # Load configuration and initialize logging system
#     ctx = util.ServerContext(APPNAME, 'default')
#     ctx.init(ctx.config_file, environment)

#     if init_resources_:
#         init_resources(ctx)

#     uri = ctx.get_database_location()
#     print('-' * 80)
#     print(uri)
#     print('-' * 80)
#     db.init(uri)


def init_resources(ctx):
    # Load resources
    global RESOURCES_INITIALIZED

    if RESOURCES_INITIALIZED:
        return

    api_base = ctx.config['api_path']

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

    environment = ctx.config.get('type')
    app.config['environment'] = environment

    # Set an extra long expiration time on access tokens for testing
    if environment == 'test':
        log.warning("Setting 'JWT_ACCESS_TOKEN_EXPIRES' to one day!")
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

    # print('-' * 80)
    # print(app.root_path)
    # print('-' * 80)

    # Actually start the server
    # app.run(*args, **kwargs)
    socketio.run(app, *args, **kwargs)



