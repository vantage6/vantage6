import os
import logging
import requests
from flask import Response, request
from http import HTTPStatus

from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies
from vantage6.backend.common.globals import HOST_URI_ENV
from vantage6.backend.common import get_server_url
from vantage6.server import db


module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def post_algorithm_store(
    data: dict, config: dict, headers: dict | None = None
) -> tuple[dict | db.AlgorithmStore, HTTPStatus]:
    """Add algorithm store to a collaboration

    Parameters
    ----------
    data : dict
        Request body as required for POST /algorithmstore request
    config : dict
        Server configuration
    headers : dict | None
        Headers to be included in the request. Usually, these will be Authorization
        headers

    Returns
    -------
    tuple[dict | db.AlgorithmStore, HTTPStatus]
        Response or AlgorithmStore object and HTTP status code
    """
    # check if algorithm store is already available for the collaboration
    collaboration_id = data.get("collaboration_id", None)
    algorithm_store_url = data["algorithm_store_url"]
    if algorithm_store_url.endswith("/"):
        algorithm_store_url = algorithm_store_url[:-1]
    existing_algorithm_stores = db.AlgorithmStore.get_by_url(algorithm_store_url)
    records_to_delete = []
    if existing_algorithm_stores:
        collabs_with_algo_store = [
            a.collaboration_id for a in existing_algorithm_stores
        ]
        if None in collabs_with_algo_store:
            return {
                "msg": "Algorithm store is already available for all collaborations"
            }, HTTPStatus.BAD_REQUEST
        if collaboration_id in collabs_with_algo_store:
            return {
                "msg": "Algorithm store is already available for this collaboration"
            }, HTTPStatus.BAD_REQUEST
        if not collaboration_id:
            # algorithm store is currently available for some
            # collaborations, but now it will be available for all of them.
            # Remove the records that only make it available to some
            # collaborations (this prevents duplicates)
            records_to_delete = existing_algorithm_stores

    # raise a warning if the algorithm store url is insecure (i.e. localhost)
    force = data.get("force", False)
    if not force and (
        "localhost" in algorithm_store_url or "127.0.0.1" in algorithm_store_url
    ):
        return {
            "msg": "Algorithm store url is insecure: localhost services "
            "may be run on any computer. Add it anyway by setting the "
            "'force' flag to true, but only do so for development servers!"
        }, HTTPStatus.BAD_REQUEST

    server_url = get_server_url(config, data.get("server_url"))
    if not server_url:
        return {
            "msg": "The 'server_url' key is required in the server "
            "configuration, or as a parameter. Please add it or ask your "
            "server administrator to specify it in the server configuration."
        }, HTTPStatus.BAD_REQUEST

    # whitelist this vantage6 server url for the algorithm store
    response, status = request_algo_store(
        algo_store_url=algorithm_store_url,
        server_url=server_url,
        endpoint="vantage6-server",
        method="post",
        force=force,
        headers=headers,
        params={"url": server_url},
    )
    if status == HTTPStatus.FORBIDDEN:
        # if whitelisting of the server at the algorithm store fails with status
        # forbidden, the store does not allow the server to be whitelisted. Check if
        # the store has open algorithms. If it does, the server can still whitelist the
        # store to get the open algorithms, but the users of this server will not be
        # able to manage anything at the store.
        if store_has_open_algorithms(algorithm_store_url, server_url):
            log.warning(
                "Could not whitelist the current server at algorithm store %s."
                " This server will only have read-only access to algorithms "
                "from the store",
                algorithm_store_url,
            )
        else:
            # if the store does not have open algorithms, the server should not
            # whitelist it as it will not be able to do anything with the store - return
            # the error message from the algorithm store
            return response, status
    elif status not in [HTTPStatus.CREATED, HTTPStatus.ALREADY_REPORTED]:
        # return error
        return response, status

    # delete and create records
    for record in records_to_delete:
        record.delete()
    algorithm_store = db.AlgorithmStore(
        name=data["name"],
        url=algorithm_store_url,
        collaboration_id=collaboration_id,
    )
    algorithm_store.save()

    return algorithm_store, HTTPStatus.CREATED


def store_has_open_algorithms(algorithm_store_url: str, server_url: str) -> bool:
    """Check if the algorithm store has open algorithms

    Parameters
    ----------
    algorithm_store_url : str
        URL to the algorithm store
    server_url: str
        URL to the current vantage6 server

    Returns
    -------
    bool
        True if the store has open algorithms, False otherwise
    """
    response, status_code = request_algo_store(
        algo_store_url=algorithm_store_url,
        server_url=server_url,
        endpoint="/policy/public",
        method="get",
    )
    if status_code != HTTPStatus.OK:
        return False
    try:
        return (
            response.json().get(StorePolicies.ALGORITHM_VIEW, None)
            == AlgorithmViewPolicies.PUBLIC
        )
    except KeyError:
        return False


def request_algo_store(
    algo_store_url: str,
    server_url: str,
    endpoint: str,
    method: str,
    force: bool = False,
    headers: dict = None,
    params: dict = None,
) -> tuple[dict | Response, HTTPStatus]:
    """
    Whitelist this vantage6 server url for the algorithm store.

    Parameters
    ----------
    algo_store_url : str
        URL to the algorithm store
    server_url : str
        URL to this vantage6 server. This is used to whitelist this server
        at the algorithm store.
    endpoint : str
        Endpoint to use at the algorithm store.
    method : str
        HTTP method to use.
    force : bool
        If True, the algorithm store will be added even if the algorithm
        store url is insecure (i.e. localhost)
    headers : dict
        Headers to be included in the request. Usually, these will be Authorization
        headers

    Returns
    -------
    tuple[dict | Response, HTTPStatus]
        The response of the algorithm store and the HTTP status. If the
        request to the algorithm store is unsuccessful, a dict with an error message is
        returned instead of the response.
    """
    is_localhost_algo_store = _contains_localhost(algo_store_url)
    try:
        response = _execute_algo_store_request(
            algo_store_url, server_url, endpoint, method, force, headers, params
        )
    except requests.exceptions.ConnectionError as exc:
        if not is_localhost_algo_store:
            log.warning("Request to algorithm store failed")
            log.exception(exc)
        response = None

    if not response and is_localhost_algo_store:
        # try again with the docker host ip
        host_uri = os.environ.get(HOST_URI_ENV, None)
        if not host_uri:
            msg = (
                "You are trying to connect to a localhost algorithm store, but this "
                "refers to the container itself. Please set the configuration option "
                "'host_uri' in the 'dev' section  of the config file to the host's IP "
                "address."
            )
            log.warning(msg)
            return {"msg": msg}, HTTPStatus.BAD_REQUEST
        algo_store_url = algo_store_url.replace("localhost", host_uri).replace(
            "127.0.0.1", host_uri
        )
        # replace double http:// with single
        algo_store_url = algo_store_url.replace("http://http://", "http://")
        try:
            response = _execute_algo_store_request(
                algo_store_url, server_url, endpoint, method, force, headers, params
            )
        except requests.exceptions.ConnectionError as exc:
            log.warning("Request to algorithm store failed")
            log.exception(exc)
            response = None

    if response is None:
        return {
            "msg": "Algorithm store cannot be reached. Make sure that "
            "it is online and that you have included the API path (default /api) at the"
            " end of the algorithm store URL"
        }, HTTPStatus.NOT_FOUND
    elif response.status_code not in [HTTPStatus.CREATED, HTTPStatus.OK]:
        try:
            msg = (
                f"Algorithm store error: {response.json()['msg']}, HTTP status: "
                f"{response.status_code}"
            )
        except (KeyError, requests.exceptions.JSONDecodeError):
            msg = (
                "Communication to algorithm store failed. HTTP status: "
                f"{response.status_code}"
            )
        return {"msg": msg}, response.status_code
    # else: server has been registered at algorithm store, proceed
    return response, response.status_code


# TODO move this to a utility module - it is also in algo store code
def _contains_localhost(url: str) -> bool:
    """Check if the url refers to localhost address"""
    return url.startswith("http://localhost") or url.startswith("http://127.0.0.1")


def _execute_algo_store_request(
    algo_store_url: str,
    server_url: str,
    endpoint: str,
    method: str,
    force: bool,
    headers: dict = None,
    param_dict: dict = None,
) -> requests.Response:
    """
    Send a request to the algorithm store to whitelist this vantage6 server
    url for the algorithm store.

    Parameters
    ----------
    algo_store_url : str
        URL to the algorithm store
    server_url : str
        URL to this vantage6 server. This is used to whitelist this server
        at the algorithm store.
    endpoint : str
        Endpoint to use at the algorithm store.
    method : str
        HTTP method to use. Choose "post" for adding the server url and
        "delete" for removing it.
    force : bool
        If True, the algorithm store will be added even if the algorithm
        store url is insecure (i.e. localhost)
    headers : dict
        Headers to be included in the request. Usually, these will be Authorization
        headers
    params : dict
        Parameters to be included in the request

    Returns
    -------
    requests.Response | None
        Response from the algorithm store. If the algorithm store is not
        reachable, None is returned
    """
    if server_url.endswith("/"):
        server_url = server_url[:-1]
    if algo_store_url.endswith("/"):
        algo_store_url = algo_store_url[:-1]

    param_dict = param_dict if param_dict is not None else {}
    if force:
        param_dict["force"] = True

    # set headers
    if not headers:
        headers = {}
    headers["server_url"] = server_url
    if "Authorization" in request.headers and not headers.get("Authorization"):
        headers["Authorization"] = request.headers["Authorization"]

    params = None
    json = None
    method = method.lower()
    if method == "get":
        request_function = requests.get
        params = param_dict
    elif method == "post":
        request_function = requests.post
        json = param_dict
    elif method == "delete":
        request_function = requests.delete
        params = param_dict
    else:
        raise ValueError(f"Method {method} not supported")

    return request_function(
        f"{algo_store_url}/{endpoint}",
        params=params,
        json=json,
        headers=headers,
    )
