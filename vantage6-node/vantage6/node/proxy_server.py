"""
This module contains a proxy server implementation that the node uses to
communicate with the server. It contains general methods for any routes, and
methods to handle tasks and results, including their encryption and decryption.
"""

import logging
import traceback
from http import HTTPStatus
from time import sleep

import requests
from flask import Flask, request
from requests import Response

from vantage6.common import base64s_to_bytes, bytes_to_base64s, logger_name
from vantage6.common.client.node_client import NodeClient

# Initialize FLASK
app = Flask(__name__)
log = logging.getLogger(logger_name(__name__))

# Need to be set when the proxy server is initialized
app.config["SERVER_IO"] = None
server_url = None

# Number of times the request is retried before the proxy server gives up
RETRY = 3


def get_method(method: str) -> callable:
    """
    Obtain http method based on string identifier

    Parameters
    ----------
    method : str
        Http method requested

    Returns
    -------
    function
        HTTP method
    """
    method_name: str = method.lower()

    method_map = {
        "get": requests.get,
        "post": requests.post,
        "patch": requests.patch,
        "put": requests.put,
        "delete": requests.delete,
    }

    return method_map.get(method_name, requests.get)


def make_proxied_request(endpoint: str) -> Response:
    """
    Helper to create proxies requests to the central server.

    Parameters
    ----------
    endpoint: str
        endpoint to be reached at the vantage6 server

    Returns
    -------
    requests.Response
        Response from the vantage6 server
    """
    present = "Authorization" in request.headers
    headers = {"Authorization": request.headers["Authorization"]} if present else None

    json = request.get_json() if request.is_json else None
    return make_request(request.method, endpoint, json, request.args, headers)


def make_request(
    method: str,
    endpoint: str,
    json: dict = None,
    params: dict = None,
    headers: dict = None,
) -> Response:
    """
    Make request to the central server

    Parameters
    ----------
    method: str
        HTTP method to be used
    endpoint: str
        endpoint of the vantage6 server
    json: dict, optional
        JSON body
    params: dict, optional
        HTTP parameters
    headers: dict, optional
        HTTP headers

    Returns
    -------
    requests.Response
        Response from the vantage6 server
    """

    method = get_method(method)

    # Forward the request to the central server. Retry when an exception is
    # raised (e.g. timeout or connection error) or when the server gives an
    # error code greater than 210
    url = f"{server_url}/{endpoint}"
    for i in range(RETRY):
        try:
            response: Response = method(url, json=json, params=params, headers=headers)
            # verify that the server gave us a valid response, else we
            # would want to try again
            if response.status_code > 210:
                log.warning(
                    "Proxy server received status code %s", response.status_code
                )
                log.warning("Error messages: %s", response.json())
                log.debug(
                    "method: %s, url: %s, json: %s, params: %s, headers: %s",
                    request.method,
                    url,
                    json,
                    params,
                    headers,
                )
                if "application/json" in response.headers.get("Content-Type"):
                    log.debug(response.json().get("msg", "no description..."))

            else:
                # Exit the retry loop because we have collected a valid
                # response
                return response

        except Exception:
            log.exception(
                "On attempt %s to reach %s, the proxy request raised an exception",
                i,
                url,
            )
            log.debug("Exception details: %s", traceback.format_exc())
            sleep(1)

    # if all attempts fail, raise an exception to be handled by its parent
    raise Exception("Proxy request failed")


def decrypt_result(run: dict) -> dict:
    """
    Decrypt the `result` from a run dictionary

    Parameters
    ----------
    run: dict
        Run dict

    Returns
    -------
    dict
        Run dict with the `result` decrypted
    """
    client: NodeClient = app.config.get("SERVER_IO")

    # if the result is a None, there is no need to decrypt that..
    try:
        if run["result"]:
            run["result"] = bytes_to_base64s(
                client.cryptor.decrypt_str_to_bytes(run["result"])
            )
    except Exception:
        log.exception(
            "Unable to decrypt and/or decode results, sending them to the algorithm..."
        )

    return run


def get_response_json_and_handle_exceptions(response: Response) -> dict | None:
    """
    Obtain json content from request response

    Parameters
    ----------
    response : requests.Response
        Requests response object

    Returns
    -------
    dict | None
        Dict containing the json body
    """
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, Exception):
        log.exception("Failed to extract JSON")
    return None


@app.route("/task", methods=["POST"])
def proxy_task():
    """
    Proxy to create tasks at the vantage6 server

    Returns
    -------
    requests.Response
        Response from the vantage6 server
    """
    # We need the server io for the decryption of the results
    client: NodeClient | None = app.config.get("SERVER_IO")
    if not client:
        log.error(
            "Task proxy request received but proxy server was not initialized properly."
        )
        return (
            {"msg": "Proxy server not initialized properly"},
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    # All requests from algorithms are unencrypted. We encrypt the input arguments
    # field for a specific organization(s) specified by the algorithm
    data = request.get_json()
    organizations = data.get("organizations")

    if not organizations:
        log.error("No organizations found in proxy request..")
        return {
            "msg": "Organizations missing from input arguments"
        }, HTTPStatus.BAD_REQUEST

    try:
        headers = {"Authorization": request.headers["Authorization"]}
    except Exception:
        log.exception("Could not extract headers from request...")

    log.debug("%s organizations", len(organizations))

    # For every organization we need to encrypt the input arguments field. This is done
    # in parallel as the client (algorithm) is waiting for a timely response.
    # For every organization the public key is retrieved so that the input arguments are
    # encrypted specifically for them.
    def encrypt_function_args(organization: dict) -> dict:
        """
        Encrypt the input arguments for a specific organization by using its private
        key.

        Parameters
        ----------
        organization : dict
            Input arguments as specified by the client (algorithm in this case) per
            organization

        Returns
        -------
        dict
            Modified organization dictionary in which the `arguments` key
            contains encrypted function arguments
        """
        arguments = organization.get("arguments", {})
        organization_id = organization.get("id")

        # retrieve public key of the organization
        log.debug("Retrieving public key of org: %s", organization_id)
        response = make_request(
            "get", f"organization/{organization_id}", headers=headers
        )
        public_key = response.json().get("public_key")

        client: NodeClient = app.config.get("SERVER_IO")
        organization["arguments"] = client.cryptor.encrypt_bytes_to_str(
            base64s_to_bytes(arguments), public_key
        )

        log.debug(
            "Function arguments succesfully encrypted for organization %s!",
            organization_id,
        )
        return organization

    if client.is_encrypted_collaboration():
        log.debug("Applying end-to-end encryption")
        data["organizations"] = [encrypt_function_args(o) for o in organizations]

    # Attempt to send the task to the central server
    try:
        response = make_request("post", "task", data, headers=headers)
    except Exception:
        log.exception("post task failed")
        return {
            "msg": "Request failed, see node logs"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    return response.content, response.status_code


@app.route("/result", methods=["GET"])
def proxy_result() -> Response:
    """
    Obtain and decrypt all results to belong to a certain task

    Parameters
    ----------
    id : int
        Task id from which the results need to be obtained

    Returns
    -------
    requests.Response
        Response from the vantage6 server
    """
    # We need the server io for the decryption of the results
    client = app.config.get("SERVER_IO")
    if not client:
        return (
            {"msg": "Proxy server not initialized properly"},
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    try:
        task_id = request.args["task_id"]
    except KeyError:
        log.exception("No task id found in request for results...")
        return {
            "msg": "No task id found in request from algorithm..."
        }, HTTPStatus.BAD_REQUEST

    # Forward the request
    try:
        response: Response = make_proxied_request(f"result?task_id={task_id}")
    except Exception:
        log.exception(f'Error on "result?task_id={task_id}"')
        return {
            "msg": "Request failed, see node logs"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    # Attempt to decrypt the results. The endpoint should have returned
    # a list of results
    results = get_response_json_and_handle_exceptions(response)
    for result in results["data"]:
        result = decrypt_result(result)

    return results, response.status_code


@app.route("/result/<int:id>", methods=["GET"])
def proxy_results(id_: int) -> Response:
    """
    Obtain and decrypt the algorithm result from the vantage6 server to be used
    by an algorithm container.

    Parameters
    ----------
    id_ : int
        Id of the result to be obtained

    Returns
    -------
    requests.Response
        Response of the vantage6 server
    """
    # We need the server io for the decryption of the results
    client: NodeClient = app.config.get("SERVER_IO")
    if not client:
        return {
            "msg": "Proxy server not initialized properly"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    # Make the proxied request
    try:
        response: Response = make_proxied_request(f"result/{id_}")
    except Exception:
        log.exception("Error on /result/<int:id>")
        return {
            "msg": "Request failed, see node logs..."
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    # Try to decrypt the results
    result = get_response_json_and_handle_exceptions(response)
    result = decrypt_result(result)

    return result, response.status_code


@app.route(
    "/<path:central_server_path>", methods=["GET", "POST", "PATCH", "PUT", "DELETE"]
)
def proxy(central_server_path: str) -> Response:
    """
    Generalized http proxy request

    Parameters
    ----------
    central_server_path : str
        The endpoint on the server to be reached

    Returns
    -------
    requests.Response
        Contains the server response
    """
    try:
        response = make_proxied_request(central_server_path)
    except Exception:
        log.exception("Generic proxy endpoint")
        return {
            "msg": "Request failed, see node logs"
        }, HTTPStatus.INTERNAL_SERVER_ERROR

    return response.content, response.status_code, response.headers.items()
