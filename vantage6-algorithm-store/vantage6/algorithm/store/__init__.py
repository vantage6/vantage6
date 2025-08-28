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
    monkey.patch_all()

import importlib
import importlib.metadata
import logging

import sqlalchemy
from flask import current_app
from flask_principal import Identity, identity_changed

from vantage6.common import logger_name
from vantage6.common.enum import StorePolicies
from vantage6.common.globals import DEFAULT_API_PATH

from vantage6.cli.context.algorithm_store import AlgorithmStoreContext

from vantage6.backend.common import Vantage6App
from vantage6.backend.common.permission import RuleNeed
from vantage6.backend.common.resource.output_schema import BaseHATEOASModelSchema

from vantage6.algorithm.store import db

# make sure the version is available
from vantage6.algorithm.store.default_roles import DefaultRole, get_default_roles
from vantage6.algorithm.store.globals import (
    RESOURCES,
    RESOURCES_PATH,
    SERVER_MODULE_NAME,
)
from vantage6.algorithm.store.model.base import Base, Database, DatabaseSessionManager
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus
from vantage6.algorithm.store.permission import PermissionManager

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

__version__ = importlib.metadata.version(__package__)


class AlgorithmStoreApp(Vantage6App):
    """
    Vantage6 server instance.

    Attributes
    ----------
    ctx : AlgorithmStoreContext
        Context object that contains the configuration of the algorithm store.
    """

    def __init__(self, ctx: AlgorithmStoreContext) -> None:
        """Create a vantage6 algorithm store application."""

        super().__init__(ctx, SERVER_MODULE_NAME)

        # setup the permission manager for the API endpoints
        self.permissions = PermissionManager(RESOURCES_PATH, RESOURCES, DefaultRole)

        # Load API resources
        self.load_resources()

        # sync policies with the database
        self.setup_policies(self.ctx.config)

        if self.ctx.config.get("dev", {}).get("disable_review", False):
            self.setup_disable_review()

        log.info("Initialization done")

    def configure_flask(self) -> None:
        """Configure the Flask settings of the vantage6 algorithm store."""
        self._configure_flask_base(DatabaseSessionManager)

    def configure_api(self) -> None:
        """Define global API output and its structure."""
        self._configure_api_base(BaseHATEOASModelSchema, Base)

    def configure_jwt(self):
        """Configure JWT authentication."""

        @self.jwt.user_lookup_loader
        def user_lookup_loader(jwt_payload: dict, jwt_headers: dict) -> db.User:
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
            db.User:
                The user identity.
            """
            identity = jwt_headers["sub"]
            auth_identity = Identity(identity)

            user = db.User.get_by_keycloak_id(identity)
            if not user:
                raise Exception("No user found for keycloak id %s", identity)

            # add role permissions
            for role in user.roles:
                for rule in role.rules:
                    auth_identity.provides.add(
                        RuleNeed(
                            name=rule.name,
                            scope=None,
                            operation=rule.operation,
                        )
                    )
            for rule in user.rules:
                auth_identity.provides.add(
                    RuleNeed(
                        name=rule.name,
                        scope=None,
                        operation=rule.operation,
                    )
                )
            identity_changed.send(
                current_app._get_current_object(), identity=auth_identity
            )
            return user

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
        try:
            [p.delete() for p in db.Policy.get()]
        except sqlalchemy.orm.exc.ObjectDeletedError:
            log.warning("Policy table is locked, skipping policy deletion")

        policies: dict = config.get("policies", {})
        for policy, policy_value in policies.items():
            if policy in [
                StorePolicies.ALLOWED_REVIEWERS.value,
                StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value,
            ]:
                if not isinstance(policy_value, list):
                    log.warning("Policy '%s' should be a list, skipping", policy)
                    continue
                for value in policy_value:
                    db.Policy(key=policy, value=value).save()
            elif policy not in StorePolicies.list():
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
            [
                AlgorithmStatus.UNDER_REVIEW,
                AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT,
            ]
        ):
            algorithm.approve()

    def start(self) -> None:
        """
        Start the server.

        Before server is really started, some database settings are checked and
        (re)set where appropriate.
        """
        self._add_default_roles(get_default_roles(), db)

        # add root user from config file if they do not exist
        if root_user := self.ctx.config.get("root_user", {}):
            root_username = root_user.get("username")
            root_organization = root_user.get("organization_id")
            if root_username:
                # if the user does not exist already, add it
                root_user = db.User.get_by_username(root_username)
                if not root_user:
                    log.warning(
                        "Creating root user. Please note that it cannot be verified at "
                        "this point that the user exists at the given vantage6 server."
                    )

                    root = db.Role.get_by_name(DefaultRole.ROOT.value)

                    root_user = db.User(
                        username=root_username,
                        organization_id=root_organization,
                        roles=[root],
                    )
                    root_user.save()
                elif len(root_user.rules) != len(db.Rule.get()):
                    log.warning("Existing root user has outdated rules, updating them.")
                    root_user.rules = db.Rule.get()
                    root_user.save()
                else:
                    log.info(
                        "The root user given in the configuration already exists -"
                        " no action taken."
                    )

                if not root_user.keycloak_id:
                    log.info("Adding keycloak id to root user")
                    self._add_keycloak_id_to_super_user(root_user)

            else:
                default_msg = (
                    "The 'root_user' section of the configuration file is "
                    "incomplete! Please set a 'username' to add a root user."
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
    ctx = AlgorithmStoreContext.from_external_config_file(
        config, system_folders, in_container=True
    )
    Database().connect(uri=ctx.get_database_uri(), allow_drop_all=False)
    return AlgorithmStoreApp(ctx).start()
