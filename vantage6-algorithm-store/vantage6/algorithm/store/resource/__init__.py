import logging
import requests
from sys import platform
from functools import wraps
from http import HTTPStatus
from flask import request

from vantage6.algorithm.store.model.rule import Operation
from vantage6.common import logger_name
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.algorithm.store.model.user import User

log = logging.getLogger(logger_name(__name__))


def authenticate_with_server(*args, **kwargs):
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
    url = url.replace('localhost', 'host.docker.internal') \
        .replace('127.0.0.1', 'host.docker.internal')

    try:
        response = requests.post(url, headers=request.headers)
    except requests.exceptions.ConnectionError as e:
        log.warning(f"Received the following exception: {e}")
        pass

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
    Decorator to verify that the user has view permission on a resource.
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
                return {'msg', msg}

            # check if view permissions for this resource are granted
            user = User.get_by_id_server(user_id)

            flag = user.can(resource, operation)

            if not flag:
                msg = f"This user is not allowed to perform this operation"
                log.warning(msg)
                return {'msg': msg}, HTTPStatus.UNAUTHORIZED

            # all good, proceed with function
            return fn(*args, **kwargs)
        return decorator
    return protection_decorator
