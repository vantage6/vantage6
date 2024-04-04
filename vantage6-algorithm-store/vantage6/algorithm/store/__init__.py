"""
The algorithm store holds the algorithms that are available to the vantage6
nodes. It is a repository of algorithms that can be coupled to a vantage6
server. The algorithms are stored in a database and can be managed through
the API. Note that is possible to couple multiple algorithm stores to a
vantage6 server. This allows both coupling a community store and a private
store to a vantage6 server.
"""

import os
from gevent import monkey

from vantage6.algorithm.store.default_roles import get_default_roles

# This is a workaround for readthedocs
if not os.environ.get("READTHEDOCS"):
    # flake8: noqa: E402 (ignore import error)
    monkey.patch_all()

# pylint: disable=C0413, C0411
import importlib
import logging
import json
import traceback

from http import HTTPStatus
from werkzeug.exceptions import HTTPException
from flask import Flask, make_response, request, send_from_directory, Request, Response
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_restful import Api
from flask_principal import Principal
from flasgger import Swagger
from pathlib import Path

from vantage6.common import logger_name
from vantage6.common.globals import APPNAME
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema
from vantage6.backend.common.globals import HOST_URI_ENV

# TODO move this to common, then remove dependency on CLI in algorithm store
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.algorithm.store._version import __version__
from vantage6.algorithm.store.globals import API_PATH
from vantage6.algorithm.store.globals import RESOURCES, SERVER_MODULE_NAME

# TODO the following are simply copies of the same files in the server - refactor
from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager, Database
from vantage6.algorithm.store import db

# TODO move server imports to common / refactor
from vantage6.algorithm.store.permission import PermissionManager

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class AlgorithmStoreApp:
    """
    Vantage6 server instance.

    Attributes
    ----------
    ctx : AlgorithmStoreContext
        Context object that contains the configuration of the algorithm store.
    """

    def __init__(self, ctx: AlgorithmStoreContext) -> None:
        """Create a vantage6-server application."""

        self.ctx = ctx

        # initialize, configure Flask
        self.app = Flask(
            SERVER_MODULE_NAME,
            root_path=Path(__file__),
            template_folder=Path(__file__).parent / "templates",
            static_folder=Path(__file__).parent / "static",
        )
        self.debug: dict = self.ctx.config.get("debug", {})
        self.configure_flask()

        # Setup SQLAlchemy and Marshmallow for marshalling/serializing
        self.ma = Marshmallow(self.app)

        # Setup Principal, granular API access manegement
        self.principal = Principal(self.app, use_sessions=False)

        # Enable cross-origin resource sharing
        self.cors = CORS(self.app)

        # SWAGGER documentation
        self.swagger = Swagger(self.app, template={})

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager()

        # Api - REST JSON-rpc
        self.api = Api(self.app)
        self.configure_api()
        self.load_resources()

        # set the server version
        self.__version__ = __version__

        # set environment variable for dev environment
        host_uri = self.ctx.config.get("dev", {}).get("host_uri")
        if host_uri:
            os.environ[HOST_URI_ENV] = host_uri

        log.info("Initialization done")

    def configure_flask(self) -> None:
        """Configure the Flask settings of the vantage6 server."""

        # let us handle exceptions
        self.app.config["PROPAGATE_EXCEPTIONS"] = True

        # Open Api Specification (f.k.a. swagger)
        self.app.config["SWAGGER"] = {
            "title": f"{APPNAME} algorithm store",
            "uiversion": "3",
            "openapi": "3.0.0",
            "version": __version__,
        }

        debug_mode = self.debug.get("flask", False)
        if debug_mode:
            log.debug("Flask debug mode enabled")
        self.app.debug = debug_mode

        def _get_request_path(request: Request) -> str:
            """
            Return request extension of request URL, e.g.
            http://localhost:5000/api/task/1 -> api/task/1

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
                "Received request: %s %s", request.method, _get_request_path(request)
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
                log.debug("%s", traceback.format_exc())
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
                "msg": "An unexpected error occurred on the server!"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        @self.app.route("/robots.txt")
        def static_from_root():
            return send_from_directory(self.app.static_folder, request.path[1:])

    def configure_api(self) -> None:
        """Define global API output and its structure."""

        # helper to create HATEOAS schemas
        BaseHATEOASModelSchema.api = self.api

        # whatever you get try to json it
        @self.api.representation("application/json")
        # pylint: disable=unused-argument
        def output_json(
            data: Base | list[Base], code: HTTPStatus, headers: dict = None
        ) -> Response:
            """
            Return jsonified data for request responses.

            Parameters
            ----------
            data: Base | list[Base]
                The data to be jsonified
            code: HTTPStatus
                The HTTP status code of the response
            headers: dict
                Additional headers to be added to the response
            """

            if isinstance(data, Base):
                data = db.jsonable(data)
            elif isinstance(data, list) and len(data) and isinstance(data[0], Base):
                data = db.jsonable(data)

            resp = make_response(json.dumps(data), code)
            resp.headers.extend(headers or {})
            return resp

    def load_resources(self) -> None:
        """Import the modules containing API resources."""

        # make services available to the endpoints, this way each endpoint can
        # make use of 'em.
        services = {
            "api": self.api,
            "config": self.ctx.config,
            "permissions": self.permissions,
        }

        for res in RESOURCES:
            module = importlib.import_module("vantage6.algorithm.store.resource." + res)
            module.setup(self.api, API_PATH, services)

    @staticmethod
    def _add_default_roles() -> None:
        for role in get_default_roles():
            if not db.Role.get_by_name(role["name"]):
                log.warning("Creating new default role %s", role["name"].value)
                new_role = db.Role(
                    name=role["name"],
                    description=role["description"],
                    rules=role["rules"],
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
        self._add_default_roles()

        # add whitelisted server and root user from config file if they do not exist
        if root_user := self.ctx.config.get("root_user", {}):
            whitelisted_uri = root_user.get("v6_server_uri")
            root_username = root_user.get("username")
            if whitelisted_uri and root_username:
                if not (v6_server := db.Vantage6Server.get_by_url(whitelisted_uri)):
                    log.debug("This server will be whitelisted: %s", whitelisted_uri)
                    v6_server = db.Vantage6Server(url=whitelisted_uri)
                    v6_server.save()

                # if the user does not exist already, add it
                if not db.User.get_by_server(
                    username=root_username, v6_server_id=v6_server.id
                ):
                    log.warning("Creating root user")

                    root = db.Role.get_by_name("Root")

                    user = db.User(
                        v6_server_id=v6_server.id,
                        username=root_username,
                        roles=[root],
                    )
                    user.save()
                else:
                    log.info(
                        "The root user given in the configuration already exists -"
                        " no action taken."
                    )

            else:
                log.warning(
                    "No v6_server_uri and/or username found in the configuration file "
                    "in the root_user section. This means no-one can alter resources on"
                    " this server, unless one or more users were already authorized to "
                    "make changes to the algorithm store previously."
                )
        else:
            log.warning(
                "No root user found in the configuration file. This means "
                "no-one can alter resources on this server, unless one or "
                "more users were already authorized to make changes to the "
                "algorithm store prevoiusly."
            )
        return self


def run_server(config: str, system_folders: bool = True) -> AlgorithmStoreApp:
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
    AlgorithmStoreApp
        A running instance of the vantage6 server
    """
    ctx = AlgorithmStoreContext.from_external_config_file(config, system_folders)
    allow_drop_all = ctx.config["allow_drop_all"]
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=allow_drop_all)
    return AlgorithmStoreApp(ctx).start()


def run_dev_server(server_app: AlgorithmStoreApp, *args, **kwargs) -> None:
    """
    Run a vantage6 development server (outside of a Docker container).

    Parameters
    ----------
    server_app: AlgorithmStoreApp
        Instance of a vantage6 server
    """
    log.warning("*" * 80)
    log.warning(" DEVELOPMENT SERVER ".center(80, "*"))
    log.warning("*" * 80)
    kwargs.setdefault("log_output", False)
    server_app.socketio.run(server_app.app, *args, **kwargs)
