import logging
import requests
from functools import wraps
from http import HTTPStatus
from flask import request

from vantage6.common import logger_name
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server

log = logging.getLogger(logger_name(__name__))


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
            # check if server to validate token is in header
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
            # TODO this is very ugly: if we are running a development server,
            # there is a good chance that the server is running on
            # localhost:5000. In that case, this request will resolve to this
            # algorithm store server itself (within Docker).
            url = f"{request.headers['Server-Url']}/token/user/validate"
            try:
                response = requests.post(url, headers=request.headers)
            except requests.exceptions.ConnectionError:
                pass

            if 'localhost' in url or '127.0.0.1' in url:
                url = url.replace('localhost', 'host.docker.internal')\
                    .replace('127.0.0.1', 'host.docker.internal')
                try:
                    response = requests.post(url, headers=request.headers)
                except requests.exceptions.ConnectionError:
                    pass

            if response is None:
                msg = 'Could not connect to server to validate token'
                log.warning(msg)
                return {'msg': msg}, HTTPStatus.INTERNAL_SERVER_ERROR
            if response.status_code != HTTPStatus.OK:
                msg = 'Token is not valid'
                log.warning(msg)
                return {'msg': msg}, HTTPStatus.UNAUTHORIZED

            # all good, proceed with function
            return fn(*args, **kwargs)
        return decorator
    return protection_decorator
