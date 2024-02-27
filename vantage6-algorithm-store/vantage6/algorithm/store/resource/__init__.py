import os
import logging
import requests
from functools import wraps
from http import HTTPStatus
from flask import request, current_app, g
from flask_principal import Identity, identity_changed
from flask_restful import Api

from vantage6.algorithm.store import PermissionManager
from vantage6.algorithm.store.model.rule import Operation
from vantage6.common import logger_name
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.permission import RuleNeed
from vantage6.backend.common.services_resources import BaseServicesResources

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
    """

    def __init__(
        self,
        api: Api,
        config: dict,
        permissions: PermissionManager,
    ):
        super().__init__(api, config)
        self.permissions = permissions

    # TODO implement this class when necessary
    # TODO move this class elsewhere?


def authenticate_with_server(*args, **kwargs):

    def __make_request(url: str) -> requests.Response:
        headers = {"Authorization": request.headers["Authorization"]}
        try:
            return requests.post(url, headers=headers)
        except requests.exceptions.ConnectionError:
            return None

    msg = 'Missing Server-Url header'
    if not request.headers.get('Server-Url'):
        log.warning(msg)
        return {'msg': msg}, HTTPStatus.BAD_REQUEST

    # check if server is whitelisted
    server = Vantage6Server.get_by_url(request.headers['Server-Url'])
    if not server:
        msg = 'Server you are trying to authenticate with is not ' \
              'whitelisted'
        log.warning(msg)
        return {'msg': msg}, HTTPStatus.UNAUTHORIZED

    # check if token is valid

    url = f"{request.headers['Server-Url']}/token/user/validate"
    # if we are looking for a localhost server, we probably have to
    # check host.docker.internal (Windows) or 172.17.0.1 (Linux)
    # instead. The user can set the environment variable HOST_URI_ENV_VAR
    # to the correct value by providing config file option
    # config['dev']['host_uri']
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

    response = __make_request(url)

    if response is None or \
            response.status_code == HTTPStatus.NOT_FOUND:
        msg = ('Could not connect to the vantage6 server. Please check'
               ' the server URL.')
        log.warning(msg)
        status_to_return = HTTPStatus.INTERNAL_SERVER_ERROR \
            if response is None else HTTPStatus.BAD_REQUEST
        return {'msg': msg}, status_to_return
    elif response.status_code != HTTPStatus.OK:
        msg = 'Token is not valid'
        log.warning(msg)
        return {'msg': msg}, HTTPStatus.UNAUTHORIZED

    return response, HTTPStatus.OK


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
            response, status = authenticate_with_server(request)

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

            response, status = authenticate_with_server(request)

            if status != HTTPStatus.OK:
                return response, status

            # can connect to server and user verified

            if "user_id" in (res := response.json()):
                user_id = res["user_id"]
            else:
                msg = "Key Error: key user_id not found"
                log.warning(msg)
                return {"msg": msg}, HTTPStatus.INTERNAL_SERVER_ERROR

            # check if view permissions for this resource are granted

            server = Vantage6Server.get_by_url(request.headers['Server-Url'])

            user = User.get_by_server(id_server=user_id, v6_server_id=server.id)

            if not user:
                msg = "User not registered in the store"
                log.warning(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED

            # if the user is registered, load the rules
            auth_identity = Identity(user_id)

            for role in user.roles:
                for rule in role.rules:
                    auth_identity.provides.add(
                        RuleNeed(
                            name=rule.name,
                            operation=rule.operation,
                        )
                    )

            identity_changed.send(
                current_app._get_current_object(), identity=auth_identity
            )

            g.user = user

            if not user.can(resource, operation):
                msg = f"This user is not allowed to perform this operation"

                log.warning(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator