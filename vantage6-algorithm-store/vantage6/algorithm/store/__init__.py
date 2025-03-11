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

# This is a workaround for readthedocs
if not os.environ.get("READTHEDOCS"):
    # flake8: noqa: E402 (ignore import error)
    monkey.patch_all()

# pylint: disable=C0413, C0411
import importlib
import logging
import json
import traceback
import datetime

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
from vantage6.common.globals import APPNAME, DEFAULT_API_PATH
from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema
from vantage6.backend.common.globals import (
    HOST_URI_ENV,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
)
from vantage6.backend.common.jsonable import jsonable
from vantage6.backend.common.mail_service import MailService

# TODO move this to common, then remove dependency on CLI in algorithm store
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.algorithm.store.model.base import Base, DatabaseSessionManager, Database
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, ReviewStatus
from vantage6.algorithm.store import db
from vantage6.algorithm.store.default_roles import get_default_roles, DefaultRole
from vantage6.algorithm.store.globals import (
    RESOURCES,
    RESOURCES_PATH,
    SERVER_MODULE_NAME,
)

from vantage6.algorithm.store.permission import PermissionManager

# make sure the version is available
from vantage6.algorithm.store._version import __version__  # noqa: F401

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
        cors_allowed_origins = self.ctx.config.get("cors_allowed_origins", "*")
        self.cors = CORS(
            self.app,
            resources={r"/*": {"origins": cors_allowed_origins}},
        )

        # SWAGGER documentation
        self.swagger = Swagger(self.app, template={})

        # setup Flask mail client
        self.mail = MailService(self.app)

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager(RESOURCES_PATH, RESOURCES, DefaultRole)

        # sync policies with the database
        self.setup_policies(self.ctx.config)

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

        # TODO v5+ remove this - for backwards compatibility of v4.6 with v4.3-4.5 we
        # are setting algorithms with empty values for the `submitted` field (new in
        # v4.6) to approved
        for algorithm in db.Algorithm.get():
            if not algorithm.submitted_at:
                algorithm.status = ReviewStatus.APPROVED.value
                algorithm.submitted_at = datetime.datetime.now(datetime.timezone.utc)
                algorithm.approved_at = datetime.datetime.now(datetime.timezone.utc)
                algorithm.save()

        if self.ctx.config.get("dev", {}).get("disable_review", False):
            self.setup_disable_review()

        log.info("Initialization done")

    def configure_flask(self) -> None:
        """Configure the Flask settings of the vantage6 algorithm store."""
        # TODO there is some duplicate code with the server here, check if it can be
        # refactored

        # let us handle exceptions
        self.app.config["PROPAGATE_EXCEPTIONS"] = True

        # Open Api Specification (f.k.a. swagger)
        self.app.config["SWAGGER"] = {
            "title": f"{APPNAME} algorithm store",
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
                log.warning("%s", traceback.format_exc())
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
                data = jsonable(data)
            elif isinstance(data, list) and len(data) and isinstance(data[0], Base):
                data = jsonable(data)

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
            "mail": self.mail,
        }

        api_path = self.ctx.config.get("api_path", DEFAULT_API_PATH)
        for res in RESOURCES:
            module = importlib.import_module("vantage6.algorithm.store.resource." + res)
            module.setup(self.api, api_path, services)

    @staticmethod
    def _add_default_roles() -> None:
        for role in get_default_roles():
            if not db.Role.get_by_name(role["name"]):
                log.warning("Creating new default role %s", role["name"])
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
                    log.warning("Updating default role %s with new rules", role["name"])
                    current_role.rules = role["rules"]
                    current_role.save()

    def setup_policies(self, config: dict) -> None:
        """
        Setup the policies for the API endpoints.

        Parameters
        ----------
        config: dict
            Configuration object containing the policies
        """
        # delete old policies from the database
        # pylint: disable=expression-not-assigned
        [p.delete() for p in db.Policy.get()]

        policies: dict = config.get("policies", {})
        for policy, policy_value in policies.items():
            # TODO v5+ remove this deprecated policy in favour of 'algorithm_view'
            if policy == "algorithms_open":
                db.Policy(
                    key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
                ).save()
                log.warning(
                    "Policy 'algorithms_open' will be deprecated in v5.0. Please use "
                    "'algorithm_view' instead."
                )
            elif policy == "algorithms_open_to_whitelisted":
                db.Policy(
                    key=StorePolicies.ALGORITHM_VIEW,
                    value=AlgorithmViewPolicies.WHITELISTED,
                ).save()
                log.warning(
                    "Policy 'algorithms_open_to_whitelisted' will be deprecated in v5.0"
                    ". Please use 'algorithm_view' instead."
                )
            elif policy in [
                StorePolicies.ALLOWED_REVIEWERS,
                StorePolicies.ALLOWED_REVIEW_ASSIGNERS,
            ]:
                if not isinstance(policy_value, list):
                    log.warning("Policy '%s' should be a list, skipping", policy)
                    continue
                for value in policy_value:
                    # get server
                    server = db.Vantage6Server.get_by_url(value["server"])
                    if not server:
                        log.warning(
                            "Server '%s' does not exist, skipping policy",
                            value["server"],
                        )
                        continue
                    # store the policy
                    db.Policy(
                        key=policy, value=f"{value['username']}|{server.url}"
                    ).save()
            elif policy not in [p.value for p in StorePolicies]:
                log.warning("Policy '%s' is not a valid policy, skipping", policy)
                continue
            elif isinstance(policy_value, list):
                log.debug("Setting multiple policies for %s:", policy)
                log.debug(", ".join(policy_value))
                for value in policy_value:
                    db.Policy(key=policy, value=value).save()
            else:
                log.debug("Setting policy %s to %s", policy, policy_value)
                db.Policy(key=policy, value=policy_value).save()

        # if the 'allow_localhost' policy is set to false, remove any whitelisted
        # localhost servers
        if not policies.get("allow_localhost", False):
            localhost_servers = db.Vantage6Server.get_localhost_servers()
            for server in localhost_servers:
                server.delete()

        # If multiple instances of the algorithm store are running and are started
        # simultaneously, it is possible that this function is run at the same time as
        # well. That may lead to double policies in the database. To prevent this, we
        # remove non-unique policies from the database.
        # TODO a more elegant solution would be to claim the policy table on the
        # database for this entire function, or so. Check if doable.
        db_policies = db.Policy.get()
        unique_policies = set()
        for policy in db_policies:
            if (policy.key, policy.value) in unique_policies:
                policy.delete()
            else:
                unique_policies.add((policy.key, policy.value))

    def setup_disable_review(self) -> None:
        """
        Change algorithm statuses on startup to disable the review process.

        This sets all algorithms that were in review to approved, effectively disabling
        the review process. For newly submitted algorithms, the review process will
        be disabled when they are submitted.

        Note that algorithms that have already been invalidated are not affected by this
        change.
        """
        # set all algorithms that are under review or awaiting review to approved
        for algorithm in db.Algorithm.get_by_algorithm_status(
            [AlgorithmStatus.UNDER_REVIEW, AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT]
        ):
            algorithm.approve()

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
            root_email = root_user.get("email")
            root_organization = root_user.get("organization_id")
            if whitelisted_uri and root_username:
                if not (v6_server := db.Vantage6Server.get_by_url(whitelisted_uri)):
                    log.info("This server will be whitelisted: %s", whitelisted_uri)
                    v6_server = db.Vantage6Server(url=whitelisted_uri)
                    v6_server.save()

                # if the user does not exist already, add it
                root_user = db.User.get_by_server(
                    username=root_username, v6_server_id=v6_server.id
                )
                if not root_user:
                    log.warning(
                        "Creating root user. Please note that it cannot be verified at "
                        "this point that the user exists at the given vantage6 server."
                    )

                    root = db.Role.get_by_name("Root")

                    user = db.User(
                        v6_server_id=v6_server.id,
                        username=root_username,
                        email=root_email,
                        organization_id=root_organization,
                        roles=[root],
                    )
                    user.save()
                elif len(root_user.rules) != len(db.Rule.get()):
                    log.warning("Existing root user has outdated rules, updating them.")
                    root_user.rules = db.Rule.get()
                    root_user.save()
                else:
                    log.info(
                        "The root user given in the configuration already exists -"
                        " no action taken."
                    )

            else:
                default_msg = (
                    "The 'root_user' section of the configuration file is "
                    "incomplete! Please include a 'v6_server_uri' and 'username' "
                    "to add this root user."
                )
                if len(db.User.get()) == 0:
                    log.warning(
                        "%s No users are defined in the database either."
                        "This means no-one can alter resources on this server.",
                        default_msg,
                    )
                else:
                    log.warning(default_msg)
        elif len(db.User.get()) == 0:
            log.warning(
                "No root user found in the configuration file, nor are users defined in"
                " the database. This means no-one can alter resources on this server."
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
