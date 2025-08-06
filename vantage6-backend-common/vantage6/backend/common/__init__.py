"""Common functionality for the vantage6 server and algorithm store."""

import importlib.metadata
import json
import logging
import os
import traceback
from abc import abstractmethod
from http import HTTPStatus
from pathlib import Path
from types import ModuleType

import requests
from flask import Flask, Request, Response, make_response, request, send_from_directory
from flask_cors import CORS
from flask_cors.core import probably_regex
from flask_jwt_extended import JWTManager
from flask_marshmallow import Marshmallow
from flask_principal import Principal
from flask_restful import Api
from werkzeug.exceptions import HTTPException

from vantage6.common import logger_name, validate_required_env_vars
from vantage6.common.globals import DEFAULT_API_PATH

from vantage6.cli.context.base_server import BaseServerContext

from vantage6.backend.common.auth import get_keycloak_id_for_user
from vantage6.backend.common.base import BaseDatabaseSessionManager, BaseModelBase
from vantage6.backend.common.globals import (
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
    HOST_URI_ENV,
    RequiredServerEnvVars,
)
from vantage6.backend.common.jsonable import jsonable
from vantage6.backend.common.mail_service import MailService
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema

__version__ = importlib.metadata.version(__package__)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class Vantage6App:
    """Base class for all vantage6 server applications."""

    def __init__(self, ctx: BaseServerContext, server_module_name: str) -> None:
        """Initialize the vantage6 app."""
        self.ctx = ctx

        # validate that the required environment variables are set
        self.validate_required_env_vars()

        # initialize, configure Flask
        self.app = Flask(
            server_module_name,
            root_path=Path(__file__),
            template_folder=Path(__file__).parent / "templates",
            static_folder=Path(__file__).parent / "static",
        )
        self.debug: dict = self.ctx.config.get("debug", {})

        # configure the flask app
        self.configure_flask()

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

        # Setup the Flask-Mail client
        self.mail = MailService(self.app)

        # Api - REST JSON-rpc
        self.api = Api(self.app)
        self.configure_api()

        # set environment variable for dev environment
        host_uri = self.ctx.config.get("dev", {}).get("host_uri")
        if host_uri:
            os.environ[HOST_URI_ENV] = host_uri

        # set the server version
        self.__version__ = __version__

    @abstractmethod
    def configure_flask(self) -> None:
        """Configure the flask app."""

    @abstractmethod
    def configure_jwt(self) -> None:
        """Configure the JWT extension."""

    @abstractmethod
    def configure_api(self) -> None:
        """Configure the API."""

    @abstractmethod
    def load_resources(self) -> None:
        """Load the resources."""

    def validate_required_env_vars(self) -> None:
        """Validate that the required environment variables are set."""
        validate_required_env_vars(RequiredServerEnvVars)

    def _get_keycloak_public_key(self) -> str:
        """Get the public key for the keycloak server."""
        response = requests.get(
            f"{os.environ.get(RequiredServerEnvVars.KEYCLOAK_URL.value)}/realms"
            f"/{os.environ.get(RequiredServerEnvVars.KEYCLOAK_REALM.value)}",
            timeout=100,
        )
        key = response.json()["public_key"]
        return f"-----BEGIN PUBLIC KEY-----\n{key}\n-----END PUBLIC KEY-----"

    def _configure_flask_base(
        self, database_session_manager: type["BaseDatabaseSessionManager"]
    ) -> None:
        """Configure the flask app."""
        # let us handle exceptions
        self.app.config["PROPAGATE_EXCEPTIONS"] = True

        # set JWT algorithms that keycloak uses
        self.app.config["JWT_ALGORITHM"] = "RS256"
        self.app.config["JWT_DECODE_ALGORITHMS"] = ["RS256"]
        # Leeway is provided for the token IAT to prevent errors that token is not yet
        # valid, which can happen if server times are drifting slightly.
        self.app.config["JWT_DECODE_LEEWAY"] = self.ctx.config.get(
            "jwt_decode_leeway", 10
        )
        self.app.config["JWT_PUBLIC_KEY"] = self._get_keycloak_public_key()
        self.app.config.setdefault("JWT_TOKEN_LOCATION", ["headers"])

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

        def _get_request_path(request_: Request) -> str:
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
            return request_.url.replace(request_.url_root, "")

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
            database_session_manager.new_session()

        @self.app.after_request
        def remove_db_session(response):
            """After every flask request.

            This will close the database session created by the
            `before_request`.
            """
            database_session_manager.clear_session()
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
            database_session_manager.clear_session()
            return error.get_response()

        @self.app.errorhandler(Exception)
        def error2_remove_db_session(_: Exception):
            """In case an exception occurs during the request.

            It is important to close the db session to avoid having dangling
            sessions.
            """
            log.exception("Exception occured during request")
            database_session_manager.clear_session()
            return {
                "msg": "An unexpected error occurred on the server!"
            }, HTTPStatus.INTERNAL_SERVER_ERROR

        @self.app.route("/robots.txt")
        def static_from_root():
            return send_from_directory(self.app.static_folder, request.path[1:])

    def _configure_api_base(
        self,
        hateoas_schema: type["BaseHATEOASModelSchema"],
        base_db_model: type["BaseModelBase"],
    ) -> None:
        """Configure the API."""

        hateoas_schema.api = self.api

        # whatever you get try to json it
        @self.api.representation("application/json")
        # pylint: disable=unused-argument
        def output_json(
            data: base_db_model | list[base_db_model],
            code: HTTPStatus,
            headers: dict = None,
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

            if isinstance(data, base_db_model):
                data = jsonable(data)
            elif (
                isinstance(data, list)
                and len(data)
                and isinstance(data[0], base_db_model)
            ):
                data = jsonable(data)

            resp = make_response(json.dumps(data), code)
            resp.headers.extend(headers or {})
            return resp

    @staticmethod
    def _add_default_roles(default_roles: list, db: ModuleType) -> None:
        for role in default_roles:
            if not db.Role.get_by_name(role["name"]):
                log.warning("Creating new default role %s", role["name"])
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
                    log.warning("Updating default role %s with new rules", role["name"])
                    current_role.rules = role["rules"]
                    current_role.save()

    def _add_keycloak_id_to_super_user(self, super_user: BaseModelBase) -> None:
        try:
            super_user.keycloak_id = get_keycloak_id_for_user(super_user.username)
            super_user.save()
        except Exception as exc:
            log.error(
                "Could not get keycloak ID for super user %s", super_user.username
            )
            log.error("This means that you cannot login as this user")
            log.exception(exc)

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


def get_server_url(
    config: dict, server_url_from_request: str | None = None
) -> str | None:
    """ "
    Get the server url from the request data, or from the configuration if it is
    not present in the request.

    Parameters
    ----------
    config : dict
        Server configuration
    server_url_from_request : str | None
        Server url from the request data.

    Returns
    -------
    str | None
        The server url
    """
    if server_url_from_request:
        return server_url_from_request
    server_url = config.get("server_url")
    # make sure that the server url ends with the api path
    api_path = config.get("api_path", DEFAULT_API_PATH)
    if server_url and not server_url.endswith(api_path):
        server_url = server_url + api_path
    return server_url
