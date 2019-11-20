#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
import importlib

TERMINAL_AVAILABLE = True
try:
    # Stuff needed for running shell in a browser
    import pty
    import select
    import subprocess
    import struct
    import fcntl
    import termios
except: 
    TERMINAL_AVAILABLE = False

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
import uuid

module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

import json

from vantage.server import db

from vantage import util
from vantage.constants import APPNAME
from vantage.server.websockets import DefaultSocketNamespace
from .resource.swagger import swagger_template


# ------------------------------------------------------------------------------
# Initialize Flask
# ------------------------------------------------------------------------------
RESOURCES_INITIALIZED = False
API_BASE = '/api'
WEB_BASE = '/app'

# Create Flask app
app = Flask(APPNAME)

app.config['JWT_AUTH_URL_RULE'] ='/api/token'

# False means refresh tokens never expire
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = False

# Open Api Specification (f.k.a. swagger)
app.config['SWAGGER'] = {
    'title': APPNAME + ' API',
    'uiversion': 3,
    'openapi': '3.0.0',
}
swagger = Swagger(app, template=swagger_template)

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
        log.debug("json-proofed")
    elif isinstance(data, list) and len(data) and isinstance(data[0], db.Base):
        data = db.jsonable(data)
        log.debug("json-list-proofed")
    log.debug(f"finished preparing {data}, lets send")

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
jwt = JWTManager(app)

@jwt.user_claims_loader
def user_claims_loader(identity):
    roles = []
    if isinstance(identity, db.User):
        type_ = 'user'
        roles = identity.roles.split(',')
    elif isinstance(identity, db.Node):
        type_ = 'node'
    elif isinstance(identity, dict):
        type_ = 'container'
    else:
        log.error(f"could not create claims from {str(identity)}")
    
    claims = {
        'type': type_,
        'roles': roles,
    }

    return claims

@jwt.user_identity_loader
def user_identity_loader(identity):

    if isinstance(identity, db.Authenticatable):
        return identity.id
    if isinstance(identity, dict):
        return identity

    log.error(f"Could not create a JSON serializable identity \
                from '{str(identity)}'")

@jwt.user_loader_callback_loader
def user_loader_callback(identity):
    if isinstance(identity, int):
        return db.Authenticatable.get(identity)
    else:
        return identity


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
    if TERMINAL_AVAILABLE:
        env = app.config['environment']
        cmd = ['ipython', '-m', 'vantage.server.shell', '-i', '--', env]

        log.debug("opening pty")
        master_fd, slave_fd = pty.openpty()

        log.debug("starting process")
        child = subprocess.Popen(
            cmd, 
            stdin=slave_fd, 
            stdout=slave_fd, 
            stderr=slave_fd
        )

        log.debug("adding process details to session")
        session.child = child
        session.fd = master_fd
        session.master_fd = master_fd
        session.slave_fd = slave_fd

        log.debug("setting window size")
        set_winsize(master_fd, 50, 50)

        log.debug("starting background task")
        socketio.start_background_task(
            read_and_forward_pty_output, 
            fd=master_fd, 
            sid=request.sid,
            child=child,
        )
        log.debug("ipython terminal backend started")
    else:
        log.debug("ipython terminal not available")


def assert_running_interpreter(start_if_required=False, child=None):
    # log.debug(f"assert_running_interpreter(start_if_required={start_if_required})")

    try:
        child = child or session.child

        if child.poll() is None:
            # log.debug("interpreter already running!")
            return True
    except (AttributeError, TypeError):
        pass


    if start_if_required:
        # log.debug("starting interpreter")
        start_interpreter()
        return True

    return False

def set_winsize(fd, row, col, xpix=0, ypix=0):
    winsize = struct.pack("HHHH", row, col, xpix, ypix)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


def read_and_forward_pty_output(fd, sid, child):
    max_read_bytes = 1024 * 20

    # fd = session.fd
    timeout_sec = 0.01

    while assert_running_interpreter(child=child):
        socketio.sleep(timeout_sec)

        (rs, ws, es) = select.select([fd], [], [], timeout_sec)

        for r in rs:
            output = os.read(r, max_read_bytes).decode()
            socketio.emit(
                "pty-output", 
                {"output": output}, 
                namespace="/pty",
                room=sid,
            )


@socketio.on("connect", namespace="/pty")
def connect_pty():
    """new client connected"""
    environment = app.config['environment']

    log.debug('-' * 80)
    log.debug('connect /pty')
    log.debug(f'environment: {environment}')
    log.debug('-' * 80)

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

        if not isinstance(auth, db.User):
            log.error("Sorry, but only users can use this websocket")
            return False

        if auth.username != 'root':
            log.error("Only root can connect to the admin channel")
            log.error(f"You're trying to connect as '{auth.username}'")
            return False

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        log.info(f'Client identified as <{session.type}>: <{session.name}>')

        assert_running_interpreter(start_if_required=True)
        return True

    return False

@socketio.on("disconnect", namespace="/pty")
def disconnect_pty():
    print(f'Client {request.sid} disconnected')
    # app.config['socket_connections'].remove(request.sid)
    # session["child"].kill()
    try:
        session.child.kill()
    except Exception as e:
        log.error("Could not kill interpreter backend!?")
        log.exception(e)



@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    """write to the child pty. The pty sees this as if you are typing in a real
    terminal.
    """
    if assert_running_interpreter():
        raw_data = data["input"].encode()
        # if raw_data == '':
        #     log.error('empty string!?')
        # else:
        #     log.info(f"input: '{raw_data}'")

        # os.write(app.config["fd"], raw_data)
        os.write(session.fd, raw_data)


@socketio.on("resize", namespace="/pty")
def resize(data):
    if assert_running_interpreter():
        set_winsize(session.fd, data["rows"], data["cols"])


@socketio.on("connect", namespace="/admin")
def connect_admin():
    environment = app.config['environment']

    print('-' * 80)
    print('connect /admin')
    print(f'environment: {environment}')
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

        if not isinstance(auth, db.User):
            log.error("Sorry, but only users can use this websocket")
            return False

        if auth.username != 'root':
            log.error("Only root can connect to the admin channel")
            log.error(f"You're trying to connect as '{auth.username}'")
            return False

        # define socket-session variables.
        session.type = auth.type
        session.name = auth.username if session.type == 'user' else auth.name
        log.info(f'Client identified as <{session.type}>: <{session.name}>')

        print(f'connecting {request.sid}')
        return True

    return False    

# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
def load_resources(api, API_BASE, resources):
    """Import the modules containing Resources."""
    for name in resources:
        module = importlib.import_module('vantage.server.resource.' + name)
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

class WebSocketLoggingHandler(logging.Handler):

    def emit(self, record):
        entry = self.format(record)
        # print(f'emitting to websocket: {entry}')

        socketio.emit('append-log', entry, namespace='/admin')


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
            # 'websocket_test',
            'stats',
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

    wslh = WebSocketLoggingHandler()
    wslh.setLevel(logging.DEBUG)
    logging.getLogger().addHandler(wslh)

    environment = ctx.config.get('type')
    app.config['environment'] = environment

    app.config['JWT_SECRET_KEY'] = ctx.config.get('jwt_secret_key', str(uuid.uuid1()))

    # Set an extra long expiration time on access tokens for testing
    if environment == 'test':
        log.warning("Setting 'JWT_ACCESS_TOKEN_EXPIRES' to one day!")
        app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)

    # print('-' * 80)
    # print(app.root_path)
    # print('-' * 80)

    # Actually start the server
    # app.run(*args, **kwargs)
    nodes, session = db.Node.get(with_session=True)
    for node in nodes:
        node.status = 'offline'
    session.commit()

    socketio.run(app, *args, **kwargs)
