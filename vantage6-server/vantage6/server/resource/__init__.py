import datetime as dt
import logging
from functools import wraps

import jwt
from flask import current_app, g, request
from flask_jwt_extended import (
    get_jwt,
    get_jwt_identity,
    verify_jwt_in_request,
)
from flask_mail import Mail
from flask_principal import Identity, identity_changed
from flask_restful import Api
from flask_socketio import SocketIO

from vantage6.common import logger_name

from vantage6.backend.common.permission import RuleNeed
from vantage6.backend.common.resource.error_handling import UnauthorizedError
from vantage6.backend.common.services_resources import BaseServicesResources

from vantage6.server import db
from vantage6.server.default_roles import DefaultRole
from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.permission import (
    PermissionManager,
    obtain_auth_collaborations,
    obtain_auth_organization,
)

log = logging.getLogger(logger_name(__name__))


class ServicesResources(BaseServicesResources):
    """
    Flask resource class for the vantage6 server.

    Adds functionality like mail, socket, permissions and the api itself.
    Also adds common helper functions.

    Attributes
    ----------
    socketio : SocketIO
        SocketIO instance
    mail : Mail
        Mail instance
    api : Api
        Api instance
    permissions : PermissionManager
        Instance of class that manages permissions
    config : dict
        Configuration dictionary
    """

    def __init__(
        self,
        socketio: SocketIO,
        mail: Mail,
        api: Api,
        permissions: PermissionManager,
        config: dict,
    ):
        super().__init__(api, config, permissions, mail)
        self.socketio = socketio

    @staticmethod
    def is_user() -> bool:
        """
        Check if the current auth is a user.

        Returns
        -------
        bool
            True if the current auth is a user, False otherwise
        """
        return g.user is not None

    @staticmethod
    def obtain_auth() -> db.Authenticatable | dict:
        """
        Read authenticatable object or dict from the flask global context.

        Returns
        -------
        db.Authenticatable | dict
            Authenticatable object or dict. Authenticatable object is either a
            user or node. Dict is for a container.
        """
        if g.user:
            return g.user
        if g.node:
            return g.node
        if g.container:
            return g.container

    @staticmethod
    def obtain_organization_id() -> int:
        """
        Obtain the organization id from the auth that is logged in.

        Returns
        -------
        int
            Organization id
        """
        if g.user:
            return g.user.organization.id
        elif g.node:
            return g.node.organization.id
        else:
            return g.container["organization_id"]

    @classmethod
    def obtain_auth_organization(cls) -> db.Organization:
        """
        Obtain the organization model from the auth that is logged in.

        Returns
        -------
        db.Organization
            Organization model
        """
        return obtain_auth_organization()

    @staticmethod
    def obtain_auth_collaborations() -> list[db.Collaboration]:
        """
        Obtain the collaborations that the auth is part of.

        Returns
        -------
        list[db.Collaboration]
            List of collaborations
        """
        return obtain_auth_collaborations()

    @staticmethod
    def obtain_auth_collaboration_ids() -> list[int]:
        """
        Obtain the collaboration ids that the auth is part of.

        Returns
        -------
        list[int]
            List of collaboration ids
        """
        return [col.id for col in obtain_auth_collaborations()]


# ------------------------------------------------------------------------------
# Helper functions/decoraters ...
# ------------------------------------------------------------------------------
def only_for(types: tuple[str] = ("user", "node", "container")) -> callable:
    """
    JWT endpoint protection decorator

    Parameters
    ----------
    types : list[str]
        List of types that are allowed to access the endpoint. Possible types
        are 'user', 'node' and 'container'.

    Returns
    -------
    function
        Decorator function that can be used to protect endpoints
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            try:
                _validate_user_or_node_token(types)
            except Exception as exc:
                if "container" not in types:
                    raise exc
                _validate_container_token()

            return fn(*args, **kwargs)

        return decorator

    return protection_decorator


def _validate_user_or_node_token(types: tuple[str]) -> None:
    """
    Validate that token belongs to a user or node.

    Parameters
    ----------
    types : tuple[str]
        List of types that are allowed to access the endpoint. Possible types
        are 'user', 'node' and 'container'.
    """
    # First verify the JWT (for user/node tokens)
    verify_jwt_in_request()
    # Get the identity and claims
    identity = get_jwt_identity()
    claims = get_jwt()

    # check that identity has access to endpoint
    g.type = claims["vantage6_client_type"]

    if g.type not in types:
        # FIXME BvB 23-10-19: user gets a 500 error, would be better to
        # get an error message with 400 code
        msg = f"{g.type}s are not allowed to access {request.url} ({request.method})"
        log.warning(msg)
        raise UnauthorizedError(msg)

    # do some specific stuff per identity
    g.user = g.container = g.node = None

    if g.type == "user":
        try:
            user = _get_and_update_authenticatable_info(identity)
        except Exception as e:
            log.error("No user found for keycloak id %s", identity)
            raise e

        g.user = user
        assert g.user.type == g.type
        log.debug("Received request from user %s (%s)", user.username, user.id)

    elif g.type == "node":
        node = _get_and_update_authenticatable_info(identity)
        g.node = node
        assert g.node.type == g.type
        log.debug("Received request from node %s (%s)", node.name, node.id)

    else:
        raise UnauthorizedError(f"Unknown entity: {g.type}")


def _validate_container_token():
    """
    Validate that token belongs to a container.
    """
    # Get the token from the Authorization header
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise Exception("Missing or invalid Authorization header")

    # Extract the token
    token = auth_header.replace("Bearer ", "")

    try:
        # Decode and verify the container token
        claims = jwt.decode(
            token,
            current_app.config["jwt_secret_key"],
            algorithms=["HS256"],
        )
    except Exception as container_error:
        log.error("Container authentication failed: %s", str(container_error))
        raise Exception("Authentication failed")

    # Verify this is a container token
    if claims.get("sub", {}).get("vantage6_client_type") != "container":
        raise Exception("Not a container token")

    # Set the container info in the global context
    g.type = "container"
    g.container = claims["sub"]
    g.user = g.node = None

    log.debug(
        "Received request from container with node id "
        f"{claims['sub']['node_id']} and task id {claims['sub']['task_id']}"
    )

    # Set up container identity and permissions
    auth_identity = Identity(claims["sub"])

    # Add container role permissions
    for rule in db.Role.get_by_name(DefaultRole.CONTAINER.value).rules:
        auth_identity.provides.add(
            RuleNeed(
                name=rule.name,
                scope=rule.scope,
                operation=rule.operation,
            )
        )

    # Send identity changed signal
    identity_changed.send(current_app._get_current_object(), identity=auth_identity)


def _get_and_update_authenticatable_info(keycloak_id: int) -> db.Authenticatable:
    """
    Get user or node from ID and update last time seen online.

    Parameters
    ----------
    keycloak_id : int
        KeycloakID of the user or node

    Returns
    -------
    db.Authenticatable
        User or node database model
    """
    auth = db.Authenticatable.get_by_keycloak_id(keycloak_id)
    auth.last_seen = dt.datetime.now(dt.timezone.utc)
    auth.save()
    return auth


# create alias decorators
with_user_or_node = only_for(
    (
        "user",
        "node",
    )
)
with_user = only_for(("user",))
with_node = only_for(("node",))
with_container = only_for(("container",))


def get_org_ids_from_collabs(auth: Authenticatable, collab_id: int = None) -> list[int]:
    """
    Get all organization ids from the collaborations the user or node is in.

    Parameters
    ----------
    auth : Authenticatable
        User or node
    collab_id : int, optional
        Collaboration id. If given, only return the organization ids of this
        collaboration. If not given, return all organization ids of all
        collaborations the user or node is in.

    Returns
    -------
    list[int]
        List of organization ids
    """
    if collab_id:
        return [
            org.id
            for col in auth.organization.collaborations
            for org in col.organizations
            if col.id == collab_id
        ]
    else:
        return [
            org.id
            for col in auth.organization.collaborations
            for org in col.organizations
        ]
