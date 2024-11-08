import os
import logging
import requests
from functools import wraps
from http import HTTPStatus
from flask import Response, request, current_app, g
from flask_mail import Mail
from flask_principal import Identity, identity_changed
from flask_restful import Api

from vantage6.algorithm.store import PermissionManager
from vantage6.algorithm.store.model.rule import Operation
from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.algorithm.store.model.user import User
from vantage6.backend.common.permission import RuleNeed
from vantage6.backend.common.services_resources import BaseServicesResources
from vantage6.algorithm.store.model.common.enums import (
    DefaultStorePolicies,
)
from vantage6.algorithm.store.model.policy import Policy

log = logging.getLogger(logger_name(__name__))


class AlgorithmStoreResources(BaseServicesResources):
    """
    Flask resource class for the algorithm store.

    Attributes
    ----------
    api : Api
        Api instance
    config: dict
        Configuration dictionary
    permissions : PermissionManager
        Permission manager instance
    mail : Mail
        Flask Mail instance
    """

    def __init__(
        self, api: Api, config: dict, permissions: PermissionManager, mail: Mail
    ):
        super().__init__(api, config, permissions, mail)


def request_from_store_to_v6_server(
    url: str,
    method: str = "get",
    params: dict = None,
    headers: dict = None,
    json: dict = None,
) -> tuple[requests.Response, int]:
    """
    Make a request from the algorithm store to the vantage6 server.

    Parameters
    ----------
    url : str
        URL of the vantage6 server endpoint to send the request to.
    method : str
        HTTP method to use for the request.
    params : dict
        Parameters to send with the request.
    headers : dict
        Headers to send with the request.
    json : dict
        JSON data to send with the request.

    Returns
    -------
    tuple[requests.Response, int]
        Response object from the request, and the status code of the response.
    """
    # First, replace localhost addresses. If we are looking for a localhost server, we
    # probably have to check host.docker.internal (Windows) or 172.17.0.1 (Linux)
    # instead. The user can set the environment variable HOST_URI_ENV_VAR
    # to the correct value by providing config file option config['dev']['host_uri']
    if "localhost" in url or "127.0.0.1" in url:
        host_uri = os.environ.get("HOST_URI_ENV_VAR", None)
        if not host_uri:
            msg = (
                "You are trying to connect to a localhost server, but "
                "this refers to the container itself. Please set the "
                " configuration option 'host_uri' in the dev section "
                " of the config file to the host's IP address."
            )
            log.warning(msg)
            return {"msg": msg}, HTTPStatus.UNAUTHORIZED
        # try replacing localhost with the host_uri from the config file
        url = url.replace("localhost", host_uri).replace("127.0.0.1", host_uri)
        # replace double http:// with single
        url = url.replace("http://http://", "http://")

    # send request
    headers = headers or {}
    headers["Authorization"] = request.headers["Authorization"]
    response = requests.request(method, url, params=params, headers=headers, json=json)
    return response, response.status_code


def request_validate_server_token(
    server_url: str,
) -> tuple[Response, int] | tuple[None, None]:
    """
    Validate the token of the server.

    Parameters
    ----------
    server_url : str
        URL of the server to validate the token of.

    Returns
    -------
    tuple[Response, int] | tuple[None, None]
        Response object from the request, or None if the server could not be reached
    """
    url = f"{server_url}/token/user/validate"
    try:
        return request_from_store_to_v6_server(url, method="post")
    except requests.exceptions.ConnectionError:
        return None, None


def _authenticate_with_server(*args, **kwargs):
    """
    Authenticate with a vantage6 server.
    """
    msg = "Missing Server-Url header"
    if not request.headers.get("Server-Url"):
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.BAD_REQUEST
    msg = "Missing Authorization header"
    if not request.headers.get("Authorization"):
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.UNAUTHORIZED

    # check if server is whitelisted
    server_url = request.headers["Server-Url"]
    server = Vantage6Server.get_by_url(server_url)
    if not server:
        msg = (
            f"Server '{server_url}' you are trying to authenticate with is not "
            "whitelisted"
        )
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.FORBIDDEN

    # check if token is valid
    response, status_code = request_validate_server_token(server_url)
    if response is None or status_code == HTTPStatus.NOT_FOUND:
        msg = "Could not connect to the vantage6 server. Please check the server URL."
        log.warning(msg)
        status_to_return = (
            HTTPStatus.INTERNAL_SERVER_ERROR
            if response is None
            else HTTPStatus.BAD_REQUEST
        )
        return {"msg": msg}, status_to_return
    elif status_code != HTTPStatus.OK:
        msg = "Token is not valid"
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.UNAUTHORIZED

    return response, HTTPStatus.OK


def _authorize_user(
    auth_response: requests.Response, resource: str, operation: Operation
) -> tuple | None:
    """
    Authorize the user to perform an operation on a resource.

    Parameters
    ----------
    auth_response : requests.Response
        Response object from the authentication request.
    resource : str
        Name of the resource to check the view permission of.
    operation: Operation
        Operation to check the permission for.

    Returns
    -------
    tuple[dict, HTTPStatus] | None
        Tuple containing an error message and status code if the user is not
        authorized, None otherwise.
    """
    # Check if user can connect to server and user logged in successfully
    try:
        username = auth_response.json()["username"]
    except Exception:
        msg = "Key Error: username not found"
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

    # check if view permissions for this resource are granted
    server = Vantage6Server.get_by_url(request.headers["Server-Url"])
    user = User.get_by_server(username=username, v6_server_id=server.id)
    if not user:
        msg = "You are not registered in this algorithm store"
        log.warning(msg)
        return {"msg": msg}, HTTPStatus.UNAUTHORIZED

    # if the user is registered, load the rules
    auth_identity = Identity(user.id)

    for role in user.roles:
        for rule in role.rules:
            auth_identity.provides.add(
                RuleNeed(name=rule.name, operation=rule.operation, scope=None)
            )

    identity_changed.send(current_app._get_current_object(), identity=auth_identity)

    g.user = user

    if not user.can(resource, operation):
        msg = (
            f"You are not allowed to perform the operation '{operation}' on resource "
            f"'{resource}'"
        )

        log.warning(msg)
        return {"msg": msg}, HTTPStatus.UNAUTHORIZED

    # User is authorized
    return None, None


def with_authentication() -> callable:
    """
    Decorator to verify that the user is authenticated with a whitelisted
    vantage6 server.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            response, status = _authenticate_with_server(request)

            if status != HTTPStatus.OK:
                return response, status

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator


def with_permission(resource: str, operation: Operation) -> callable:
    """
    Decorator to verify that the user has as a permission on a resource.
    Parameters
    ----------
    resource : str
        Name of the resource to check the view permission of.
    operation: Operation
        Operation to check the permission for.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            response, status = _authenticate_with_server(request)

            if status != HTTPStatus.OK:
                return response, status

            response, status = _authorize_user(response, resource, operation)
            if response is not None:
                return response, status

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator


def with_permission_to_view_algorithms() -> callable:
    """
    Decorator to verify that the user has as a permission on a resource.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(self, *args, **kwargs):
            policies = Policy.get_as_dict()
            # check if everyone has permission to view algorithms
            algorithm_view_policy = policies.get(
                StorePolicies.ALGORITHM_VIEW, DefaultStorePolicies.ALGORITHM_VIEW.value
            )

            # check if user is trying to view algorithms that are not approved by review
            # or have been invalidated - these algorithms always require authentication
            # even when algorithms are open to all
            request_args = request.args or {}
            request_approved = not (
                request_args.get("awaiting_reviewer_assignment")
                or request_args.get("under_review")
                or request_args.get("in_review_process")
                or request_args.get("invalidated")
            )

            # TODO v5+ remove this deprecated policy "algorithms_open"
            anyone_can_view = policies.get("algorithms_open", False)
            if (
                anyone_can_view or algorithm_view_policy == AlgorithmViewPolicies.PUBLIC
            ) and request_approved:
                return fn(self, *args, **kwargs)

            # not everyone has permission: authenticate with server
            response, status = _authenticate_with_server(request)
            if status != HTTPStatus.OK:
                return response, status

            # check if all authenticated users have permission to view algorithms
            # TODO v5+ remove this deprecated policy
            any_user_can_view = policies.get("algorithms_open_to_whitelisted", False)
            if (
                any_user_can_view
                or algorithm_view_policy == AlgorithmViewPolicies.WHITELISTED
            ):
                return fn(self, *args, **kwargs)

            # not all authenticated users have permission: authorize user
            response, status = _authorize_user(response, "algorithm", Operation.VIEW)
            if response is not None:
                return response, status

            # all good, proceed with function
            return fn(self, *args, **kwargs)

        return decorator

    return protection_decorator
