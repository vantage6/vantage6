# -*- coding: utf-8 -*-
from gevent import monkey

# flake8: noqa: E402 (ignore import error)
monkey.patch_all()

import importlib
import logging
import os
import uuid
import json

from werkzeug.exceptions import HTTPException
from flasgger import Swagger
from flask import Flask, make_response, current_app, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_mail import Mail
from flask_principal import Principal, Identity, identity_changed
from flask_socketio import SocketIO

from vantage6.cli.context import ServerContext
from vantage6.cli.rabbitmq.queue_manager import get_rabbitmq_uri
from vantage6.server import db
from vantage6.server.resource._schema import HATEOASModelSchema
from vantage6.server.model.base import DatabaseSessionManager, Database
from vantage6.common import logger_name
from vantage6.server.permission import RuleNeed, PermissionManager
from vantage6.server.globals import (
    APPNAME,
    JWT_ACCESS_TOKEN_EXPIRES,
    JWT_TEST_ACCESS_TOKEN_EXPIRES,
    RESOURCES,
    SUPER_USER_INFO,
    REFRESH_TOKENS_EXPIRE
)
from vantage6.server.resource.swagger import swagger_template
from vantage6.server._version import __version__
from vantage6.server.mail_service import MailService
from vantage6.server.websockets import DefaultSocketNamespace


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class ServerApp:
    """Vantage6 server instance."""

    def __init__(self, ctx):
        """Create a vantage6-server application."""

        self.ctx = ctx

        # initialize, configure Flask
        self.app = Flask(APPNAME, root_path=os.path.dirname(__file__))
        self.configure_flask()

        # Setup SQLAlchemy and Marshmallow for marshalling/serializing
        self.ma = Marshmallow(self.app)

        # Setup the Flask-JWT-Extended extension (JWT: JSON Web Token)
        self.jwt = JWTManager(self.app)
        self.configure_jwt()

        # Setup Principal, granular API access manegement
        self.principal = Principal(self.app, use_sessions=False)

        # Enable cross-origin resource sharing
        self.cors = CORS(self.app)

        # SWAGGER documentation
        self.swagger = Swagger(self.app, template=swagger_template)

        # Setup the Flask-Mail client
        self.mail = MailService(self.app, Mail(self.app))

        # Setup websocket channel
        self.socketio = self.setup_socket_connection()

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager()

        # Api - REST JSON-rpc
        self.api = Api(self.app)
        self.configure_api()
        self.load_resources()

        # make specific log settings (muting etc)
        self.configure_logging()
        log.info("Initialization done")

        # set the serv
        self.__version__ = __version__

    def setup_socket_connection(self):

        rabbit_config = self.ctx.config.get('rabbitmq')
        if rabbit_config and 'uri' in rabbit_config:
            msg_queue = rabbit_config['uri']
        else:
            msg_queue = get_rabbitmq_uri(rabbit_config, self.ctx.name) \
                if rabbit_config else None

        log.debug(f'Connecting to msg queue: {msg_queue}')
        try:
            socketio = SocketIO(
                self.app,
                async_mode='gevent_uwsgi',
                message_queue=msg_queue,
                ping_timeout=60,
                cors_allowed_origins='*'
            )
        except Exception as e:
            log.warning('Default socketio settings failed, attempt to run '
                        'without gevent_uwsgi packages! This leads to '
                        'performance issues and possible issues concerning '
                        'the websocket channels!')
            log.debug(e)
            socketio = SocketIO(
                self.app,
                message_queue=msg_queue,
                ping_timeout=60
            )

        # FIXME: temporary fix to get socket object into the namespace class
        DefaultSocketNamespace.socketio = socketio
        socketio.on_namespace(DefaultSocketNamespace("/tasks"))

        return socketio

    @staticmethod
    def configure_logging():
        """Turn 3rd party loggers off."""

        # Prevent logging from urllib3
        logging.getLogger("urllib3").setLevel(logging.WARNING)
        logging.getLogger("socketIO-client").setLevel(logging.WARNING)
        logging.getLogger("engineio.server").setLevel(logging.WARNING)
        logging.getLogger("socketio.server").setLevel(logging.WARNING)

    def configure_flask(self):
        """All flask config settings should go here."""

        # let us handle exceptions
        self.app.config['PROPAGATE_EXCEPTIONS'] = True

        # patch where to obtain token
        self.app.config['JWT_AUTH_URL_RULE'] = '/api/token'

        # False means refresh tokens never expire
        self.app.config['JWT_REFRESH_TOKEN_EXPIRES'] = REFRESH_TOKENS_EXPIRE

        # If no secret is set in the config file, one is generated. This
        # implies that all (even refresh) tokens will be invalidated on restart
        self.app.config['JWT_SECRET_KEY'] = self.ctx.config.get(
            'jwt_secret_key',
            str(uuid.uuid1())
        )

        # Default expiration time
        self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = JWT_ACCESS_TOKEN_EXPIRES

        # Set an extra long expiration time on access tokens for testing
        # TODO: this does not seem needed...
        environment = self.ctx.config.get('type')
        self.app.config['environment'] = environment
        if environment == 'test':
            log.warning("Setting 'JWT_ACCESS_TOKEN_EXPIRES' to one day!")
            self.app.config['JWT_ACCESS_TOKEN_EXPIRES'] = \
                JWT_TEST_ACCESS_TOKEN_EXPIRES

        # Open Api Specification (f.k.a. swagger)
        self.app.config['SWAGGER'] = {
            'title': APPNAME,
            'uiversion': "3",
            'openapi': '3.0.0',
            'version': __version__
        }

        # Mail settings
        mail_config = self.ctx.config.get("smtp", {})
        self.app.config["MAIL_PORT"] = mail_config.get("port", 1025)
        self.app.config["MAIL_SERVER"] = mail_config.get("server", "localhost")
        self.app.config["MAIL_USERNAME"] = mail_config.get(
            "username",
            "support@vantage6.ai"
        )
        self.app.config["MAIL_PASSWORD"] = mail_config.get("password", "")
        self.app.config["MAIL_USE_TLS"] = mail_config.get("MAIL_USE_TLS",
                                                          True)
        self.app.config["MAIL_USE_SSL"] = mail_config.get("MAIL_USE_SSL",
                                                          False)

        # before request
        @self.app.before_request
        def set_db_session():
            """Before every flask request method.
            This will obtain a (scoped) db session from the session factory
            that is linked to the flask request global `g`. In every endpoint
            we then can access the database by using this session. We ensure
            that the session is removed (and uncommited changes are rolled
            back) at the end of every request.
            """
            DatabaseSessionManager.new_session()

        @self.app.after_request
        def remove_db_session(response):
            """After every flask request.
            This will close the database session created by the
            `before_request`.
            """
            DatabaseSessionManager.clear_session()
            return response

        @self.app.errorhandler(HTTPException)
        def error_remove_db_session(error):
            """In case an HTTP-exception occurs during the request.
            It is important to close the db session to avoid having dangling
            sessions.
            """
            log.warn(f'Error occured during request @ {request.url}')
            log.debug(error)
            DatabaseSessionManager.clear_session()
            return error.get_response()

        @self.app.errorhandler(Exception)
        def error2_remove_db_session(error):
            """In case an HTTP-exception occurs during the request.
            It is important to close the db session to avoid having dangling
            sessions.
            """
            log.warn('Error occured during request')
            log.debug(error)
            DatabaseSessionManager.clear_session()
            return {'msg': f'Error: {error}'}, 500

    def configure_api(self):
        """"Define global API output."""

        # helper to create HATEOAS schemas
        HATEOASModelSchema.api = self.api

        # whatever you get try to json it
        @self.api.representation('application/json')
        def output_json(data, code, headers=None):

            if isinstance(data, db.Base):
                data = db.jsonable(data)
            elif isinstance(data, list) and len(data) and \
                    isinstance(data[0], db.Base):
                data = db.jsonable(data)

            resp = make_response(json.dumps(data), code)
            resp.headers.extend(headers or {})
            return resp

    def configure_jwt(self):
        """Load user and its claims."""

        @self.jwt.user_claims_loader
        def user_claims_loader(identity):
            roles = []
            if isinstance(identity, db.User):
                type_ = 'user'
                roles = [role.name for role in identity.roles]

            elif isinstance(identity, db.Node):
                type_ = 'node'
            elif isinstance(identity, dict):
                type_ = 'container'
            else:
                log.error(f"could not create claims from {str(identity)}")
                return

            claims = {
                'type': type_,
                'roles': roles,
            }

            return claims

        @self.jwt.user_identity_loader
        def user_identity_loader(identity):
            """"JSON serializing identity to be used by create_access_token."""
            if isinstance(identity, db.Authenticatable):
                return identity.id
            if isinstance(identity, dict):
                return identity

            log.error(f"Could not create a JSON serializable identity \
                        from '{str(identity)}'")

        @self.jwt.user_loader_callback_loader
        def user_loader_callback(identity):
            auth_identity = Identity(identity)
            # in case of a user or node an auth id is shared as identity,
            if isinstance(identity, int):

                # auth_identity = Identity(identity)

                auth = db.Authenticatable.get(identity)

                if isinstance(auth, db.Node):

                    for rule in db.Role.get_by_name("node").rules:
                        auth_identity.provides.add(
                                RuleNeed(
                                    name=rule.name,
                                    scope=rule.scope,
                                    operation=rule.operation
                                )
                            )

                if isinstance(auth, db.User):

                    # add role permissions
                    for role in auth.roles:
                        for rule in role.rules:
                            auth_identity.provides.add(
                                RuleNeed(
                                    name=rule.name,
                                    scope=rule.scope,
                                    operation=rule.operation
                                )
                            )

                    # add 'extra' permissions
                    for rule in auth.rules:
                        auth_identity.provides.add(
                            RuleNeed(
                                name=rule.name,
                                scope=rule.scope,
                                operation=rule.operation
                            )
                        )

                identity_changed.send(current_app._get_current_object(),
                                      identity=auth_identity)

                return auth
            else:

                for rule in db.Role.get_by_name("container").rules:
                    auth_identity.provides.add(
                        RuleNeed(
                            name=rule.name,
                            scope=rule.scope,
                            operation=rule.operation
                        )
                    )
                identity_changed.send(current_app._get_current_object(),
                                      identity=auth_identity)
                log.debug(identity)
                return identity

    def load_resources(self):
        """Import the modules containing Resources."""

        # make services available to the endpoints, this way each endpoint can
        # make use of 'em.
        services = {
            "socketio": self.socketio,
            "mail": self.mail,
            "api": self.api,
            "permissions": self.permissions
        }

        for res in RESOURCES:
            module = importlib.import_module('vantage6.server.resource.' + res)
            module.setup(self.api, self.ctx.config['api_path'], services)

    def start(self, *args, **kwargs):
        """Run the server.
        """

        # create root user if it is not in the DB yet
        try:
            db.User.get_by_username(SUPER_USER_INFO['username'])
        except Exception:
            log.warn("No root user found! Is this the first run?")

            log.debug("Creating organization for root user")
            org = db.Organization(name="root")

            log.warn("Creating root role...")
            root = db.Role(
                name="Root",
                description="Super role"
            )
            root.rules = db.Rule.get()

            log.warn(f"Creating root user: "
                     f"username={SUPER_USER_INFO['username']}, "
                     f"password={SUPER_USER_INFO['password']}")

            user = db.User(username=SUPER_USER_INFO['username'], roles=[root],
                           organization=org, email="root@domain.ext",
                           password=SUPER_USER_INFO['password'])
            user.save()

        # set all nodes to offline
        # TODO: this is *not* the way
        nodes = db.Node.get()
        for node in nodes:
            node.status = 'offline'
            node.save()
        # session.commit()

        return self


def run_server(config: str, environment: str = 'prod',
               system_folders: bool = True):
    ctx = ServerContext.from_external_config_file(
        config,
        environment,
        system_folders
    )
    allow_drop_all = ctx.config["allow_drop_all"]
    Database().connect(uri=ctx.get_database_uri(),
                       allow_drop_all=allow_drop_all)
    return ServerApp(ctx).start()


def run_dev_server(server_app: ServerApp, *args, **kwargs):
    log.warn('*'*80)
    log.warn(' DEVELOPMENT SERVER '.center(80, '*'))
    log.warn('*'*80)
    kwargs.setdefault('log_output', False)
    server_app.socketio.run(server_app.app, *args, **kwargs)
