"""
The server has a central function in the vantage6 architecture. It stores
in the database which organizations, collaborations, users, etc.
exist. It allows the users and nodes to authenticate and subsequently interact
through the API the server hosts. Finally, it also communicates with
authenticated nodes and users via the socketIO server that is run here.
"""

import os
from gevent import monkey

# This is a workaround for readthedocs
if not os.environ.get("READTHEDOCS"):
    # flake8: noqa: E402 (ignore import error)
    monkey.patch_all()

# pylint: disable=wrong-import-position, wrong-import-order
import importlib
import logging
import uuid
import json
import time
import datetime as dt
import traceback
import requests
from keycloak import KeycloakOpenID

from http import HTTPStatus
from werkzeug.exceptions import HTTPException
from flasgger import Swagger
from flask import (
    Flask,
    make_response,
    current_app,
    request,
    send_from_directory,
    Request,
    Response,
)
from flask_cors import CORS
from flask_cors.core import probably_regex
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_principal import Principal, Identity, identity_changed
from flask_socketio import SocketIO
from threading import Thread
from pathlib import Path
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common import logger_name, split_rabbitmq_uri
from vantage6.common.globals import PING_INTERVAL_SECONDS, AuthStatus
from vantage6.backend.common.globals import (
    HOST_URI_ENV,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
    RequiredServerEnvVars,
)
from vantage6.backend.common.jsonable import jsonable
from vantage6.backend.common.permission import RuleNeed
from vantage6.backend.common import Vantage6App
from vantage6.backend.common.mail_service import MailService
from vantage6.cli.context.server import ServerContext
from vantage6.server.model.base import DatabaseSessionManager, Database
from vantage6.server.permission import PermissionManager
from vantage6.server import db
from vantage6.server.resource.common.output_schema import HATEOASModelSchema
from vantage6.server.globals import (
    APPNAME,
    RESOURCES,
    RESOURCES_PATH,
    SUPER_USER_INFO,
    SERVER_MODULE_NAME,
)
from vantage6.server.resource.common.swagger_templates import swagger_template
from vantage6.server.websockets import DefaultSocketNamespace
from vantage6.server.default_roles import get_default_roles, DefaultRole
from vantage6.server.controller import cleanup

# make sure the version is available
from vantage6.server._version import __version__  # noqa: F401

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class ServerApp(Vantage6App):
    """
    Vantage6 server instance.

    Attributes
    ----------
    ctx : ServerContext
        Context object that contains the configuration of the server.
    """

    def __init__(self, ctx: ServerContext) -> None:
        """Create a vantage6-server application."""

        self.ctx = ctx

        # validate that the required environment variables are set
        self.validate_required_env_vars()

        # initialize, configure Flask
        self.app = Flask(
            SERVER_MODULE_NAME,
            root_path=Path(__file__),
            template_folder=Path(__file__).parent / "templates",
            static_folder=Path(__file__).parent / "static",
        )
        self.debug: dict = self.ctx.config.get("debug", {})
        self.configure_flask(self.ctx.config.get("api_path"))

        # Setup SQLAlchemy and Marshmallow for marshalling/serializing
        self.ma = Marshmallow(self.app)

        # Setup the Flask-JWT-Extended extension (JWT: JSON Web Token)
        self.jwt = JWTManager(self.app)
        self.configure_jwt()

        # Setup Principal, granular API access manegement
        self.principal = Principal(self.app, use_sessions=False)

        # Enable cross-origin resource sharing. Note that Flask-CORS interprets
        # the origins as regular expressions.
        cors_allowed_origins = self.ctx.config.get("cors_allowed_origins", "*")
        self._warn_if_cors_regex(cors_allowed_origins)
        self.cors = CORS(
            self.app,
            resources={r"/*": {"origins": cors_allowed_origins}},
        )

        # SWAGGER documentation
        self.swagger = Swagger(self.app, template=swagger_template)

        # Setup the Flask-Mail client
        self.mail = MailService(self.app)

        # Setup websocket channel
        self.socketio = self.setup_socket_connection()

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager(RESOURCES_PATH, RESOURCES, DefaultRole)

        # Api - REST JSON-rpc
        self.api = Api(self.app)
        self.configure_api()
        self.load_resources()

        # set environment variable for dev environment
        host_uri = self.ctx.config.get("dev", {}).get("host_uri")
        if host_uri:
            os.environ[HOST_URI_ENV] = host_uri

        # couple any algoritm stores to the server if defined in config. This should be
        # done after the resources are loaded to ensure that rules are set up
        # TODO reactivate this option - and then remove it in dev setup script - #1983
        # self.couple_algorithm_stores()

        # TODO v5+ clean this up (simply delete community store URL update). This
        # change is here to prevent errors when going from v4.3-4.7 to 4.8+.
        # Because in v4.8, the algorithm store's API path was made
        # flexible, the /api from then on had to be included in the database
        community_stores = db.AlgorithmStore.get_by_url(
            "https://store.cotopaxi.vantage6.ai"
        )
        if community_stores:
            # only need to update first one (there shouldn't be more than 1 anyway)
            community_store = community_stores[0]
            log.warning(
                "Updating community store URL to include '/api'. This change is"
                " necessary as you are updating to v4.8"
            )
            community_store.url = f"{community_store.url}/api"
            community_store.save()

        # set the server version
        self.__version__ = __version__

        if self.ctx.config.get("runs_data_cleanup_days"):
            log.info(
                "Results older than %s days will be removed",
                self.ctx.config.get("runs_data_cleanup_days"),
            )
            t_cleanup = Thread(target=self.__runs_data_cleanup_worker, daemon=True)
            t_cleanup.start()

        # set up socket ping/pong
        log.debug("Starting thread to set node status")
        t = Thread(target=self.__node_status_worker, daemon=True)
        t.start()

        log.info("Initialization done")

    @staticmethod
    def _warn_if_cors_regex(origins: str | list[str]) -> None:
        """
        Give a warning if CORS origins are regular expressions. This will not work
        properly for socket events (Flask-SocketIO checks for string equality and does
        not use regex).

        Note that we are using the `probably_regex` function from Flask-CORS to check
        if the origins are probably regular expressions - the Flask implementation for
        determining if it is a regex is a bit hacky (see
        https://github.com/corydolphin/flask-cors/blob/3.0.10/flask_cors/core.py#L275-L285)
        and Flask-CORS doesn't currently offer an opt out of regex's altogether.

        Parameters
        ----------
        origins: str | list[str]
            The origins to check
        """
        if isinstance(origins, str):
            origins = [origins]

        for origin in origins:
            if probably_regex(origin) and not origin == "*":
                log.warning(
                    "CORS origin '%s' is a regular expression. Socket events sent from "
                    "this origin will not be handled properly.",
                    origin,
                )

    def setup_socket_connection(self) -> SocketIO:
        """
        Setup a socket connection. If a message queue is defined, connect the
        socket to the message queue. Otherwise, use the default socketio
        settings.

        Returns
        -------
        SocketIO
            SocketIO object
        """
        msg_queue = self.ctx.config.get("rabbitmq", {}).get("uri")
        if msg_queue:
            try:
                splitted_rabbit_uri = split_rabbitmq_uri(msg_queue)
                log.debug(
                    "Connecting to msg queue: amqp://<user>:<pass>@%s:%s/%s",
                    splitted_rabbit_uri["host"],
                    splitted_rabbit_uri["port"],
                    splitted_rabbit_uri["vhost"],
                )
            except Exception:
                log.warning(
                    "Failed to parse RabbitMQ URI. Will try to use the provided"
                    "URI to connect, but it may likely fail."
                )

        debug_mode = self.debug.get("socketio", False)
        if debug_mode:
            log.debug("SocketIO debug mode enabled")

        cors_settings = self.ctx.config.get("cors_allowed_origins", "*")
        try:
            socketio = SocketIO(
                self.app,
                async_mode="gevent_uwsgi",
                message_queue=msg_queue,
                ping_timeout=60,
                cors_allowed_origins=cors_settings,
                logger=debug_mode,
                engineio_logger=debug_mode,
                always_connect=True,
            )
        except Exception as e:
            log.warning(
                "Default socketio settings failed, attempt to run "
                "without gevent_uwsgi packages! This leads to "
                "performance issues and possible issues concerning "
                "the websocket channels!"
            )
            log.debug(e)
            socketio = SocketIO(
                self.app,
                message_queue=msg_queue,
                ping_timeout=60,
                cors_allowed_origins=cors_settings,
                logger=debug_mode,
                engineio_logger=debug_mode,
                always_connect=True,
            )

        # FIXME: temporary fix to get socket object into the namespace class
        DefaultSocketNamespace.socketio = socketio
        socketio.on_namespace(DefaultSocketNamespace("/tasks"))

        return socketio

    def configure_flask(self, api_path: str) -> None:
        """
        Configure the Flask settings of the vantage6 server.

        Parameters
        ----------
        api_path: str
            The base path of the API
        """

        # let us handle exceptions
        self.app.config["PROPAGATE_EXCEPTIONS"] = True

        # set JWT algorithms that keycloak uses
        self.app.config["JWT_ALGORITHM"] = "RS256"
        self.app.config["JWT_DECODE_ALGORITHMS"] = ["RS256"]

        self.app.config["JWT_PUBLIC_KEY"] = self._get_keycloak_public_key()

        # set JWT secret key
        self.app.config["jwt_secret_key"] = self.ctx.config.get(
            "jwt_secret_key", str(uuid.uuid4())
        )

        # Open Api Specification (f.k.a. swagger)
        self.app.config["SWAGGER"] = {
            "title": APPNAME,
            "uiversion": "3",
            "openapi": "3.0.0",
            "version": __version__,
        }

        # Mail settings
        mail_config = self.ctx.config.get("smtp", {})
        self.app.config["MAIL_PORT"] = mail_config.get("port", 1025)
        self.app.config["MAIL_SERVER"] = mail_config.get("server", "localhost")
        self.app.config["MAIL_USERNAME"] = mail_config.get(
            "username", DEFAULT_SUPPORT_EMAIL_ADDRESS
        )
        self.app.config["MAIL_PASSWORD"] = mail_config.get("password", "")
        self.app.config["MAIL_USE_TLS"] = mail_config.get("MAIL_USE_TLS", True)
        self.app.config["MAIL_USE_SSL"] = mail_config.get("MAIL_USE_SSL", False)
        debug_mode = self.debug.get("flask", False)
        if debug_mode:
            log.debug("Flask debug mode enabled")
        self.app.debug = debug_mode

        def _get_request_path(request: Request) -> str:
            """
            Return request extension of request URL, e.g.
            http://localhost:7601/api/task/1 -> api/task/1

            Parameters
            ----------
            request: Request
                Flask request object

            Returns
            -------
            string:
                The endpoint path of the request
            """
            return request.url.replace(request.url_root, "")

        # before request
        @self.app.before_request
        def do_before_request():
            """Before every flask request method."""
            # Add log message before each request
            log.debug(
                f"Received request: {request.method} {_get_request_path(request)}"
            )

            # This will obtain a (scoped) db session from the session factory
            # that is linked to the flask request global `g`. In every endpoint
            # we then can access the database by using this session. We ensure
            # that the session is removed (and uncommited changes are rolled
            # back) at the end of every request.
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
        def error_remove_db_session(error: HTTPException):
            """In case an HTTP-exception occurs during the request.

            It is important to close the db session to avoid having dangling
            sessions.
            """
            if error.code == 404:
                log.debug("404 error for route '%s'", _get_request_path(request))
            else:
                log.warning("HTTP Exception occured during request")
                log.debug("Details exception: %s", traceback.format_exc())
            DatabaseSessionManager.clear_session()
            return error.get_response()

        @self.app.errorhandler(Exception)
        def error2_remove_db_session(error):
            """In case an exception occurs during the request.

            It is important to close the db session to avoid having dangling
            sessions.
            """
            log.exception("Exception occured during request")
            DatabaseSessionManager.clear_session()
            return {
                "msg": f"An unexpected error occurred on the server!"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        @self.app.route("/robots.txt")
        def static_from_root():
            return send_from_directory(self.app.static_folder, request.path[1:])

    @staticmethod
    def _get_keycloak_public_key():
        response = requests.get(
            f"{os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value)}/realms"
            "/vantage6"
        )
        key = response.json()["public_key"]
        return f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"

    def configure_api(self) -> None:
        """Define global API output and its structure."""

        # helper to create HATEOAS schemas
        HATEOASModelSchema.api = self.api

        # whatever you get try to json it
        @self.api.representation("application/json")
        # pylint: disable=unused-argument
        def output_json(
            data: db.Base | list[db.Base], code: HTTPStatus, headers: dict = None
        ) -> Response:
            """
            Return jsonified data for request responses.

            Parameters
            ----------
            data: db.Base | list[db.Base]
                The data to be jsonified
            code: HTTPStatus
                The HTTP status code of the response
            headers: dict
                Additional headers to be added to the response
            """

            if isinstance(data, db.Base):
                data = jsonable(data)
            elif isinstance(data, list) and len(data) and isinstance(data[0], db.Base):
                data = jsonable(data)

            resp = make_response(json.dumps(data), code)
            resp.headers.extend(headers or {})
            return resp

    def configure_jwt(self):
        """Configure JWT authentication."""

        @self.jwt.user_lookup_loader
        # pylint: disable=unused-argument
        def user_lookup_loader(
            jwt_payload: dict, jwt_headers: dict
        ) -> db.Authenticatable | dict:
            """
            Load the user, node or container instance from the JWT payload.

            Parameters
            ----------
            jwt_payload: dict
                The JWT payload
            jwt_headers: dict
                The JWT headers

            Returns
            -------
            db.Authenticatable | dict:
                The user, node or container identity. If the identity is a
                container, a dict is returned.
            """
            identity = jwt_headers["sub"]
            auth_identity = Identity(identity)
            try:
                auth = db.Authenticatable.get_by_keycloak_id(identity)
            except Exception:
                raise Exception("No user or node found for keycloak id %s", identity)

            # in case of a user or node, we find an authenticated entity
            if isinstance(auth, db.Node):
                for rule in db.Role.get_by_name(DefaultRole.NODE).rules:
                    auth_identity.provides.add(
                        RuleNeed(
                            name=rule.name,
                            scope=rule.scope,
                            operation=rule.operation,
                        )
                    )

            elif isinstance(auth, db.User):
                # add role permissions
                for role in auth.roles:
                    for rule in role.rules:
                        auth_identity.provides.add(
                            RuleNeed(
                                name=rule.name,
                                scope=rule.scope,
                                operation=rule.operation,
                            )
                        )

                # add 'extra' permissions
                for rule in auth.rules:
                    auth_identity.provides.add(
                        RuleNeed(
                            name=rule.name,
                            scope=rule.scope,
                            operation=rule.operation,
                        )
                    )

            identity_changed.send(
                current_app._get_current_object(), identity=auth_identity
            )

            return auth

    def load_resources(self) -> None:
        """Import the modules containing API resources."""

        # make services available to the endpoints, this way each endpoint can
        # make use of 'em.
        services = {
            "socketio": self.socketio,
            "mail": self.mail,
            "api": self.api,
            "permissions": self.permissions,
            "config": self.ctx.config,
        }

        for res in RESOURCES:
            module = importlib.import_module("vantage6.server.resource." + res)
            module.setup(self.api, self.ctx.config["api_path"], services)

    # TODO consider moving this method elsewhere. This is not trivial at the
    # moment because of the circular import issue with `db`, see
    # https://github.com/vantage6/vantage6/issues/53
    @staticmethod
    def _add_default_roles() -> None:
        for role in get_default_roles(db):
            if not db.Role.get_by_name(role["name"]):
                log.warning("Creating new default role %s...", role["name"].value)
                new_role = db.Role(
                    name=role["name"],
                    description=role["description"],
                    rules=role["rules"],
                    is_default_role=True,
                )
                new_role.save()
            else:
                current_role = db.Role.get_by_name(role["name"])
                # check that the rules are the same. Use set() to compare without order
                if set(current_role.rules) != set(role["rules"]):
                    log.warning(
                        "Updating default role %s with new rules", role["name"].value
                    )
                    current_role.rules = role["rules"]
                    current_role.save()

    def start(self) -> None:
        """
        Start the server.

        Before server is really started, some database settings are checked and
        (re)set where appropriate.
        """
        # add default roles (if they don't exist yet)
        self._add_default_roles()

        # create root user if it is not in the DB yet
        try:
            admin_user = db.User.get_by_username(SUPER_USER_INFO["username"])
        except Exception:
            log.warning("No root user found! Is this the first run?")
            admin_user = self._create_super_user()

        if not admin_user.keycloak_id:
            self._add_keycloak_id_to_super_user(admin_user)

        return self

    def _create_super_user(self) -> None:
        """
        Create the super user.

        This method is used when the server is started for the first time.
        """
        # sanity check, this function should never be called in any other
        # context than the first run of the server
        try:
            db.User.get_by_username(SUPER_USER_INFO["username"])
            raise Exception("Attempted to create super user when it already existed!")
        except NoResultFound:
            pass

        log.debug("Creating organization for root user")
        if not (org := db.Organization.get_by_name("root")):
            org = db.Organization(name="root")

        # TODO use constant instead of 'Root' literal
        root = db.Role.get_by_name(DefaultRole.ROOT)

        # TODO no longer use any default root username / password
        log.warning(
            f"Creating super user ({SUPER_USER_INFO['username']})"
            " with default password!"
        )

        user = db.User(
            username=SUPER_USER_INFO["username"],
            roles=[root],
            organization=org,
            # TODO: should we use RFC6761's "invalid." here?
            email="admin@domain.ext",
        )
        user.save()
        return user

    def _add_keycloak_id_to_super_user(self, super_user: db.User) -> None:
        keycloak_openid = KeycloakOpenID(
            server_url=os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value),
            client_id=os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT.value),
            realm_name=os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value),
            client_secret_key=os.environ.get(
                RequiredServerEnvVars.KEYCLOAK_ADMIN_CLIENT_SECRET.value
            ),
        )
        token = keycloak_openid.token(
            os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_USERNAME.value),
            os.environ.get(RequiredServerEnvVars.KEYCLOAK_ADMIN_PASSWORD.value),
        )
        decoded_token = keycloak_openid.decode_token(token["access_token"])
        super_user.keycloak_id = decoded_token["sub"]
        super_user.save()

    def __node_status_worker(self) -> None:
        """
        Set node status to offline if they haven't send a ping message in a
        while.
        """
        # start periodic check if nodes are responsive
        while True:
            # Send ping event
            try:
                before_wait = dt.datetime.now(dt.timezone.utc)

                # Wait a while to give nodes opportunity to pong. This interval
                # is a bit longer than the interval at which the nodes ping,
                # because we want to make sure that the nodes have had time to
                # respond.
                time.sleep(PING_INTERVAL_SECONDS + 5)

                # Check for each node that is online if they have responded.
                # Otherwise set them to offline.
                online_status_nodes = db.Node.get_online_nodes()
                for node in online_status_nodes:
                    if node.last_seen.replace(tzinfo=dt.timezone.utc) < before_wait:
                        node.status = AuthStatus.OFFLINE.value
                        node.save()
            except Exception:
                log.exception("Node-status thread had an exception")
                time.sleep(PING_INTERVAL_SECONDS)

    def __runs_data_cleanup_worker(self):
        """Start a background thread to clean up data from old Runs."""
        # NOTE/TODO: this is a very simple implementation, horizonal scaling is
        # not being taken into account. We'd probably only need one worker per
        # database, not per server instance (for example).
        include_input = self.ctx.config.get("runs_data_cleanup_include_input", False)
        while True:
            try:
                cleanup.cleanup_runs_data(
                    self.ctx.config.get("runs_data_cleanup_days"),
                    include_input=include_input,
                )
            except Exception as e:
                log.error("Results cleanup failed. Will try again in one hour.")
                log.exception(e)
            # simple for now: check every hour
            time.sleep(3600)

    # TODO Enable this functionality again - see issue #1983
    # def couple_algorithm_stores(self) -> None:
    #     """Couple algorithm stores to the server.

    #     Checks if default algorithm stores are defined in the configuration and if so,
    #     couples them to the server.
    #     """
    #     algorithm_stores = self.ctx.config.get("algorithm_stores", [])
    #     server_url = get_server_url(self.ctx.config)
    #     if algorithm_stores and not server_url:
    #         log.warning(
    #             "Algorithm stores are defined in the configuration, but the server "
    #             "url is not. Skipping coupling of algorithm stores."
    #         )
    #         return
    #     if algorithm_stores:
    #         # TODO in the future it may change that not just any algorithm store can
    #         # be added to this server - in that case show a useful error below
    #         # (automated coupling is not possible for such cases I think?)

    #         # couple the stores
    #         for store in algorithm_stores:
    #             if not (name := store.get("name")):
    #                 log.warning("Algorithm store has no name, skipping coupling")
    #                 continue
    #             elif not (url := store.get("url")):
    #                 log.warning(
    #                     "Algorithm store %s has no url, skipping coupling", name
    #                 )
    #                 continue
    #             store = db.AlgorithmStore.get_by_url(url)
    #             if not store:
    #                 response, status = add_algorithm_store_to_database(
    #                     {
    #                         "name": name,
    #                         "algorithm_store_url": url,
    #                         "server_url": server_url,
    #                     },
    #                     self.ctx.config,
    #                 )
    #                 if status == HTTPStatus.CREATED:
    #                     log.info(
    #                         "Algorithm store '%s' at %s has been coupled to the server",
    #                         name,
    #                         url,
    #                     )
    #                 else:
    #                     log.error(
    #                         "Failed to couple algorithm store '%s' at %s to the server:"
    #                         " %s",
    #                         name,
    #                         url,
    #                         response["msg"],
    #                     )
    #             # else: store already exists, no need to couple it again


def run_server(config: str, system_folders: bool = True) -> ServerApp:
    """
    Run a vantage6 server.

    Parameters
    ----------
    config: str
        Configuration file path
    system_folders: bool
        Whether to use system or user folders. Default is True.

    Returns
    -------
    ServerApp
        A running instance of the vantage6 server
    """
    ctx = ServerContext.from_external_config_file(config, system_folders)
    allow_drop_all = ctx.config["allow_drop_all"]
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=allow_drop_all)
    return ServerApp(ctx).start()


def run_dev_server(server_app: ServerApp, *args, **kwargs) -> None:
    """
    Run a vantage6 development server (outside of a Docker container).

    Parameters
    ----------
    server_app: ServerApp
        Instance of a vantage6 server
    """
    log.warn("*" * 80)
    log.warn(" DEVELOPMENT SERVER ".center(80, "*"))
    log.warn("*" * 80)
    kwargs.setdefault("log_output", False)
    server_app.socketio.run(server_app.app, *args, **kwargs)
