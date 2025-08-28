"""
The server has a central function in the vantage6 architecture. It stores
in the database which organizations, collaborations, users, etc.
exist. It allows the users and nodes to authenticate and subsequently interact
through the API the server hosts. Finally, it also communicates with
authenticated nodes and users via the socketIO server that is run here.
"""

import importlib.metadata
import os

from gevent import monkey

from vantage6.server.algo_store_communication import add_algorithm_store_to_database

# This is a workaround for readthedocs
if not os.environ.get("READTHEDOCS"):
    # flake8: noqa: E402 (ignore import error)
    monkey.patch_all()

# pylint: disable=wrong-import-position, wrong-import-order
import datetime as dt
import importlib
import logging
import time
import uuid
from http import HTTPStatus
from threading import Thread

from flask import current_app
from flask_principal import Identity, identity_changed
from flask_socketio import SocketIO
from sqlalchemy.orm.exc import NoResultFound

from vantage6.common import logger_name, split_rabbitmq_uri
from vantage6.common.globals import (
    DEFAULT_PROMETHEUS_EXPORTER_PORT,
    PING_INTERVAL_SECONDS,
    AuthStatus,
)

from vantage6.cli.context.server import ServerContext

from vantage6.backend.common import Vantage6App
from vantage6.backend.common.metrics import Metrics, start_prometheus_exporter
from vantage6.backend.common.permission import RuleNeed

from vantage6.server import db
from vantage6.server.controller import cleanup
from vantage6.server.default_roles import DefaultRole, get_default_roles
from vantage6.server.globals import (
    RESOURCES,
    RESOURCES_PATH,
    SERVER_MODULE_NAME,
    SUPER_USER_INFO,
)
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.permission import PermissionManager
from vantage6.server.resource.common.output_schema import HATEOASModelSchema
from vantage6.server.websockets import DefaultSocketNamespace

__version__ = importlib.metadata.version(__package__)

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

        super().__init__(ctx, SERVER_MODULE_NAME)

        self.metrics = Metrics(labels=["node_id", "platform", "os"])
        # Setup websocket channel
        self.socketio = self.setup_socket_connection()

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager(RESOURCES_PATH, RESOURCES, DefaultRole)

        # Load API resources
        self.load_resources()

        # couple any algoritm stores to the server if defined in config. This should be
        # done after the resources are loaded to ensure that rules are set up
        self.couple_algorithm_stores()

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

        prometheus_config = self.ctx.config.get("prometheus", {})
        if prometheus_config.get("enabled", False):
            start_prometheus_exporter(
                port=prometheus_config.get(
                    "exporter_port", DEFAULT_PROMETHEUS_EXPORTER_PORT
                )
            )

        log.info("Initialization done")

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

        namespace = DefaultSocketNamespace("/tasks", socketio, self.metrics)
        socketio.on_namespace(namespace)

        return socketio

    def configure_flask(self) -> None:
        """
        Configure the Flask settings of the vantage6 server.

        Parameters
        ----------
        api_path: str
            The base path of the API
        """

        self._configure_flask_base(DatabaseSessionManager)

        # set JWT secret key to generate container tokens
        self.app.config["jwt_secret_key"] = self.ctx.config.get(
            "jwt_secret_key", str(uuid.uuid4())
        )

    def configure_api(self) -> None:
        """Define global API output and its structure."""
        self._configure_api_base(HATEOASModelSchema, db.Base)

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
                for rule in db.Role.get_by_name(DefaultRole.NODE.value).rules:
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

    def start(self) -> None:
        """
        Start the server.

        Before server is really started, some database settings are checked and
        (re)set where appropriate.
        """
        # add default roles (if they don't exist yet)
        self._add_default_roles(get_default_roles(db), db)

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

        root = db.Role.get_by_name(DefaultRole.ROOT.value)

        # TODO no longer use any default root username / password
        log.warning(
            f"Creating super user ({SUPER_USER_INFO['username']})"
            " with default password!"
        )

        user = db.User(
            username=SUPER_USER_INFO["username"],
            roles=[root],
            organization=org,
        )
        user.save()
        return user

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
        include_args = self.ctx.config.get("runs_data_cleanup_include_args", False)
        while True:
            try:
                cleanup.cleanup_runs_data(
                    self.ctx.config.get("runs_data_cleanup_days"),
                    include_args=include_args,
                )
            except Exception as e:
                log.error("Results cleanup failed. Will try again in one hour.")
                log.exception(e)
            # simple for now: check every hour
            time.sleep(3600)

    def couple_algorithm_stores(self) -> None:
        """Couple algorithm stores to the server.

        Checks if default algorithm stores are defined in the configuration and if so,
        couples them to the server.
        """
        algorithm_stores = self.ctx.config.get("algorithm_stores", [])
        if algorithm_stores:
            # couple the stores
            for store in algorithm_stores:
                if not (name := store.get("name")):
                    log.warning("Algorithm store has no name, skipping coupling")
                    continue
                elif not (url := store.get("url")):
                    log.warning(
                        "Algorithm store %s has no url, skipping coupling", name
                    )
                    continue
                elif not (api_path := store.get("api_path")):
                    log.warning(
                        "Algorithm store %s has no api_path, skipping coupling", name
                    )
                    continue
                store = db.AlgorithmStore.get_by_url(url, api_path)
                if not store:
                    response, status = add_algorithm_store_to_database(
                        {
                            "name": name,
                            "algorithm_store_url": url,
                            "api_path": api_path,
                        },
                    )
                    if status == HTTPStatus.CREATED:
                        log.info(
                            "Algorithm store '%s' at %s has been coupled to the server",
                            name,
                            url,
                        )
                    else:
                        log.error(
                            "Failed to couple algorithm store '%s' at %s to the server:"
                            " %s",
                            name,
                            url,
                            response["msg"],
                        )
                else:
                    log.info(
                        "Algorithm store '%s' at %s is already coupled to the server",
                        name,
                        url,
                    )


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
    ctx = ServerContext.from_external_config_file(
        config, system_folders, in_container=True
    )
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=False)
    return ServerApp(ctx).start()
