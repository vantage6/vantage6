import logging
import os
import time
from http import HTTPStatus
from urllib.parse import urlparse

import requests
from flask import Response
from keycloak import KeycloakOpenID

from vantage6.common.globals import DEFAULT_API_PATH, HTTP_LOCALHOST, LINUX_LOCALHOST

from vantage6.backend.common.auth import get_service_account_in_keycloak
from vantage6.backend.common.globals import (
    DEFAULT_HQ_STORE_READER_KEYCLOAK_CLIENT,
    RequiredBackendEnvVars,
)

from vantage6.hq import db
from vantage6.hq.globals import HQ_STORE_READER_CLIENT_ENV_VAR

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)

# seconds before HQ's token for algorithm stores expires that it is renewed
HQ_STORE_TOKEN_RENEWAL_MARGIN = 30

class HQStoreToken:
    """
    The token HQ uses to call algorithm stores.

    The token is issued to HQ itself (not to a user) and is only valid at algorithm
    stores, where it only allows reading approved algorithms. It is kept until shortly
    before it expires.
    """

    _access_token: str | None = None
    _expires_at: float = 0

    @classmethod
    def get(cls) -> str:
        """
        Get a valid token, requesting a new one if needed.

        Returns
        -------
        str
            Access token
        """
        if cls._access_token is None or cls._expires_at <= time.time():
            cls._renew()
        return cls._access_token

    @classmethod
    def _renew(cls) -> None:
        """Request a new token from Keycloak."""
        client_name = os.environ.get(
            HQ_STORE_READER_CLIENT_ENV_VAR, DEFAULT_HQ_STORE_READER_KEYCLOAK_CLIENT
        )
        keycloak_openid = KeycloakOpenID(
            server_url=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_URL.value),
            realm_name=os.environ.get(RequiredBackendEnvVars.KEYCLOAK_REALM.value),
            client_id=client_name,
            client_secret_key=get_service_account_in_keycloak(
                client_name
            ).client_secret,
        )
        token = keycloak_openid.token(grant_type="client_credentials")
        cls._access_token = token["access_token"]
        cls._expires_at = (
            time.time() + token["expires_in"] - HQ_STORE_TOKEN_RENEWAL_MARGIN
        )


def _check_algorithm_store_online(algorithm_store_url: str) -> bool:
    """
    Check if the algorithm store is online and reachable

    Parameters
    ----------
    algorithm_store_url : str
        URL to the algorithm store

    Returns
    -------
    bool
        True if the algorithm store is online and reachable, False otherwise
    """
    log.debug("Checking if algorithm store is online at %s", algorithm_store_url)
    try:
        _, status_code = request_algo_store(
            algo_store_url=algorithm_store_url,
            endpoint="/version",
            method="get",
        )
        return status_code == HTTPStatus.OK
    except requests.exceptions.ConnectionError:
        return False


def add_algorithm_store_to_database(
    data: dict,
) -> tuple[dict | db.AlgorithmStore, HTTPStatus]:
    """Add algorithm store to a collaboration

    Parameters
    ----------
    data : dict
        Request body as required for POST /algorithmstore request

    Returns
    -------
    tuple[dict | db.AlgorithmStore, HTTPStatus]
        Response or AlgorithmStore object and HTTP status code
    """
    # check if algorithm store is already available for the collaboration
    collaboration_id = data.get("collaboration_id", None)
    algorithm_store_url = data["algorithm_store_url"]
    algorithm_store_url = algorithm_store_url.removesuffix("/")
    api_path = data.get("api_path", DEFAULT_API_PATH)

    if not _check_algorithm_store_online(f"{algorithm_store_url}{api_path}"):
        return {
            "msg": "Algorithm store cannot be found. Is it online and is the URL "
            "correct?"
        }, HTTPStatus.BAD_REQUEST

    # Delete existing records that will be replaced by the new one
    records_to_delete = []
    existing_algorithm_stores = db.AlgorithmStore.get_by_url(
        algorithm_store_url, api_path
    )
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
    for record in records_to_delete:
        record.delete()

    # Create new record. If not given, whether the store uses HQ's Keycloak is copied
    # from other records of the same store.
    algorithm_store = db.AlgorithmStore(
        name=data["name"],
        url=algorithm_store_url,
        api_path=api_path,
        collaboration_id=collaboration_id,
        uses_hq_keycloak=data.get(
            "uses_hq_keycloak",
            any(store.uses_hq_keycloak for store in existing_algorithm_stores),
        ),
    )
    algorithm_store.save()

    return algorithm_store, HTTPStatus.CREATED


def request_algo_store(
    algo_store_url: str,
    endpoint: str,
    method: str,
    params: dict | None = None,
    headers: dict | None = None,
) -> tuple[dict | Response, HTTPStatus]:
    """
    Whitelist this vantage6 HQ url for the algorithm store.

    Parameters
    ----------
    algo_store_url : str
        URL to the algorithm store
    endpoint : str
        Endpoint to use at the algorithm store.
    method : str
        HTTP method to use.
    params : dict
        Parameters to be included in the request
    headers : dict, optional
        Headers to be included in the request

    Returns
    -------
    tuple[dict | Response, HTTPStatus]
        The response of the algorithm store and the HTTP status. If the
        request to the algorithm store is unsuccessful, a dict with an error message is
        returned instead of the response.
    """
    is_localhost_algo_store = _contains_localhost(algo_store_url)
    log.debug("Calling algorithm store at %s/%s", algo_store_url, endpoint)
    try:
        response = _execute_algo_store_request(
            algo_store_url, endpoint, method, params, headers
        )
    except requests.exceptions.ConnectionError as exc:
        if not is_localhost_algo_store:
            log.exception("Request to algorithm store failed", exc_info=exc)
        response = None

    # if the algorithm store is on localhost, we need to look for the local kubernetes
    # service and use that instead
    local_store_url = os.environ.get("LOCAL_STORE_URL")
    if not response and is_localhost_algo_store and local_store_url:
        parsed_url = urlparse(algo_store_url)
        path = parsed_url.path

        # LOCAL_STORE_URL is already a complete URL, just append the path
        # The Kubernetes service listens on port 80 (service port), not the target port
        new_url = f"{local_store_url}{path}"
        log.debug("Retry adding local store with kubernetes service URL: %s", new_url)
        try:
            response = _execute_algo_store_request(
                new_url, endpoint, method, params, headers
            )
        except requests.exceptions.ConnectionError as exc:
            log.exception("Request to algorithm store failed", exc_info=exc)
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
    # else: HQ has been registered at algorithm store, proceed
    return response, response.status_code


def _contains_localhost(url: str) -> bool:
    """Check if the url refers to localhost address"""
    return url.startswith((HTTP_LOCALHOST, LINUX_LOCALHOST))


def _execute_algo_store_request(
    algo_store_url: str,
    endpoint: str,
    method: str,
    param_dict: dict | None = None,
    headers: dict | None = None,
) -> requests.Response:
    """
    Send a request to the algorithm store to whitelist this vantage6 HQ URL for the
    algorithm store.

    Parameters
    ----------
    algo_store_url : str
        URL to the algorithm store
    endpoint : str
        Endpoint to use at the algorithm store.
    method : str
        HTTP method to use. Choose "post" for adding the HQ URL and "delete" for
        removing it.
    params : dict, optional
        Parameters to be included in the request
    headers : dict, optional
        Headers to be included in the request

    Returns
    -------
    requests.Response | None
        Response from the algorithm store. If the algorithm store is not
        reachable, None is returned
    """
    # Remove trailing slash from base URL
    algo_store_url = algo_store_url.removesuffix("/")

    # Remove leading slash from endpoint to avoid double slashes
    endpoint = endpoint.removeprefix("/")

    param_dict = param_dict if param_dict is not None else {}
    headers = headers if headers is not None else {}

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
