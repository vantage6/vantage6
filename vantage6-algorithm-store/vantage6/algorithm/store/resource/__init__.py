import os
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
            def __make_request(url: str) -> requests.Response:
                try:
                    return requests.post(url, headers=request.headers)
                except requests.exceptions.ConnectionError:
                    return None

            # check if server to validate token is in header
            msg = "Missing Server-Url header"
            if not request.headers.get("Server-Url"):
                log.warning(msg)
                return {"msg": msg}, HTTPStatus.BAD_REQUEST

            # check if server is whitelisted
            server = Vantage6Server.get_by_url(request.headers["Server-Url"])
            if not server:
                msg = "Server you are trying to authenticate with is not whitelisted"
                log.warning(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED

            # check if token is valid
            url = f"{request.headers['Server-Url']}/token/user/validate"
            response = __make_request(url)

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

            if response is None or response.status_code == HTTPStatus.NOT_FOUND:
                msg = (
                    "Could not connect to the vantage6 server. Please check"
                    " the server URL."
                )
                log.warning(msg)
                status_to_return = (
                    HTTPStatus.INTERNAL_SERVER_ERROR
                    if response is None
                    else HTTPStatus.BAD_REQUEST
                )
                return {"msg": msg}, status_to_return
            elif response.status_code != HTTPStatus.OK:
                msg = f"Token could not be validated (code {response.status_code})"
                log.warning(msg)
                return {"msg": msg}, HTTPStatus.UNAUTHORIZED

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator
