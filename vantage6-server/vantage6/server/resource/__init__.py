import datetime as dt
import logging

from functools import wraps

from flask import g, request
from flask_restful import Api
from flask_mail import Mail
from flask_jwt_extended import get_jwt, get_jwt_identity, jwt_required
from flask_socketio import SocketIO


from vantage6.common import logger_name
from vantage6.backend.common.services_resources import BaseServicesResources
from vantage6.server import db
from vantage6.server.utils import obtain_auth_collaborations, obtain_auth_organization
from vantage6.server.model.authenticatable import Authenticatable
from vantage6.server.permission import PermissionManager

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
        Union[db.Authenticatable, dict]
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
            # decode JWT-token
            identity = get_jwt_identity()
            claims = get_jwt()

            # check that identity has access to endpoint
            g.type = claims["client_type"]

            if g.type not in types:
                # FIXME BvB 23-10-19: user gets a 500 error, would be better to
                # get an error message with 400 code
                msg = (
                    f"{g.type}s are not allowed to access {request.url} "
                    f"({request.method})"
                )
                log.warning(msg)
                raise Exception(msg)

            # do some specific stuff per identity
            g.user = g.container = g.node = None

            if g.type == "user":
                user = get_and_update_authenticatable_info(identity)
                g.user = user
                assert g.user.type == g.type
                log.debug(f"Received request from user {user.username} ({user.id})")

            elif g.type == "node":
                node = get_and_update_authenticatable_info(identity)
                g.node = node
                assert g.node.type == g.type
                log.debug(f"Received request from node {node.name} ({node.id})")

            elif g.type == "container":
                g.container = identity
                log.debug(
                    "Received request from container with node id "
                    f"{identity['node_id']} and task id {identity['task_id']}"
                )

            else:
                raise Exception(f"Unknown entity: {g.type}")

            return fn(*args, **kwargs)

        return jwt_required()(decorator)

    return protection_decorator


def get_and_update_authenticatable_info(auth_id: int) -> db.Authenticatable:
    """
    Get user or node from ID and update last time seen online.

    Parameters
    ----------
    auth_id : int
        ID of the user or node

    Returns
    -------
    db.Authenticatable
        User or node database model
    """
    auth = db.Authenticatable.get(auth_id)
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


def parse_datetime(
    date: str | dt.datetime = None, default: dt.datetime = None
) -> dt.datetime:
    """
    Utility function to parse a datetime string.

    Parameters
    ----------
    date : str | datetime.datetime, optional
        Datetime string
    default : datetime.datetime, optional
        Default datetime to return if `dt` is None

    Returns
    -------
    datetime.datetime
        Datetime object
    """
    if date:
        if isinstance(date, str):
            converter = "%Y-%m-%dT%H:%M:%S.%f"
            if date.endswith("+00:00"):
                converter += "%z"  # parse timezone
            return dt.datetime.strptime(date, converter)
        else:
            # convert datetime to UTC
            return date.astimezone(dt.timezone.utc)
    return default


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
