"""
This module contains a proxy server implementation that the node uses to
communicate with the server. It contains general methods for any routes, and
methods to handle tasks and results, including their encryption and decryption.

(!) Not to be confused with the squid proxy that allows algorithm containers
to access other places in the network.
"""

import requests
import logging
import traceback

from time import sleep
from http import HTTPStatus
from requests import Response

from flask import Flask, request, stream_with_context, Response as FlaskResponse

from vantage6.common import bytes_to_base64s, base64s_to_bytes, logger_name
from vantage6.common.client.node_client import NodeClient
from vantage6.common.client.utils import is_uuid
from vantage6.common.globals import STRING_ENCODING


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
            run["result"] = bytes_to_base64s(client.cryptor.decrypt(run["result"]))
    except Exception:
        log.exception(
            "Unable to decrypt and/or decode results, sending them "
            "to the algorithm..."
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
    client: NodeClient = app.config.get("SERVER_IO")
    if not client:
        log.error(
            "Task proxy request received but proxy server was not "
            "initialized properly."
        )
        return (
            {"msg": "Proxy server not initialized properly"},
            HTTPStatus.INTERNAL_SERVER_ERROR,
        )

    # All requests from algorithms are unencrypted. We encrypt the input
    # field for a specific organization(s) specified by the algorithm
    data = request.get_json()
    organizations = data.get("organizations")

    if not organizations:
        log.error("No organizations found in proxy request..")
        return {"msg": "Organizations missing from input"}, HTTPStatus.BAD_REQUEST

    try:
        headers = {"Authorization": request.headers["Authorization"]}
    except Exception:
        log.exception("Could not extract headers from request...")

    log.debug("%s organizations", len(organizations))

    # For every organization we need to encrypt the input field. This is done
    # in parallel as the client (algorithm) is waiting for a timely response.
    # For every organization the public key is retrieved an the input is
    # encrypted specifically for them.
    def encrypt_input(organization_id: int, input_: dict) -> str:
        """
        Encrypt the input for a specific organization by using its public key.
        Parameters
        ----------
        organization_id : int
            ID of the organization
        input_ : dict
            Input as specified by the client (algorithm in this case)
        Returns
        -------
        str
            Encrypted input as a string
        """
        # retrieve public key of the organization
        log.debug("Retrieving public key of org: %s", organization_id)
        response = make_request(
            "get", f"organization/{organization_id}", headers=headers
        )
        public_key = response.json().get("public_key")

        # Encrypt the input field
        client: NodeClient = app.config.get("SERVER_IO")
        # If blob store is enabled, we skip base64 encoding of the message.
        encrypted_input = client.cryptor.encrypt_bytes_to_str(
            base64s_to_bytes(input_), public_key
        )

        log.debug("Input successfully encrypted for organization %s!", organization_id)
        return encrypted_input

    if client.is_encrypted_collaboration():
        log.debug("Applying end-to-end encryption")

        for org in organizations:
            if not client.check_if_blob_store_enabled():
                if is_uuid(org.get("input")):
                    log.warning(
                        "Input is a UUID, are you sending blob based inputs "
                        "to a non-blob store enabled server?"
                    )
                org["input"] = encrypt_input(org["id"], org.get("input", {}))
        data["organizations"] = organizations
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
        if not result["blob_storage_used"] or result["blob_storage_used"] == False:
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
    if not result["blob_storage_used"] or result["blob_storage_used"] == False:
        result = decrypt_result(result)

    return result, response.status_code


@app.route("/blobstream/<string:id>", methods=["GET"])
def stream_handler(id: str) -> FlaskResponse:
    """
    Proxy stream handler for GET requests, filestream a blob by its id from the Azure server.
    Proxied_request and standard response are not used here,
    as this function is specifically designed to handle streaming of blobs
    without loading the entire content into memory.


    Parameters
    ----------
    id : str
        The id of the blob to be streamed.

    Returns
    -------
    FlaskResponse
        A Flask response object containing the streamed blob data.
        If the blob is successfully streamed, it returns a response
        with the content type set to "application/octet-stream" and the
        content disposition set to attachment.
        If an error occurs, it returns an error message with the appropriate HTTP status code.
    """

    log.debug("Proxy stream handler called with id: %s", id)
    headers = {}
    for h in ["Authorization", "Content-Type", "Content-Length"]:
        if h in request.headers:
            headers[h] = request.headers[h]
    method = get_method(request.method)
    url = f"{server_url}/blobstream/{id}"
    log.debug("Making proxied request to %s", url)

    backend_response = method(url, stream=True, params=request.args, headers=headers)

    log.debug("Received response with status code %s", backend_response.status_code)

    if backend_response.status_code > 210:
        log.warning(
            "Proxy server received status code %s", backend_response.status_code
        )
        try:
            log.warning("Error messages: %s", backend_response.json())
        except Exception:
            log.warning(
                "Could not decode error response as JSON. Response text: %s",
                backend_response.text,
            )
        log.debug(
            "method: %s, url: %s, params: %s, headers: %s",
            request.method,
            url,
            request.args,
            headers,
        )
        return (
            backend_response.content,
            backend_response.status_code,
            backend_response.headers.items(),
        )
    client: NodeClient = app.config.get("SERVER_IO")

    # Only decrypt if the response is successful and content type is as expected
    content_type = backend_response.headers.get("Content-Type", "")
    if (
        backend_response.status_code <= 210
        and "application/octet-stream" in content_type
    ):
        return FlaskResponse(
            stream_with_context(client.cryptor.decrypt_stream(backend_response.raw)),
            status=backend_response.status_code,
            headers=dict(backend_response.headers),
            content_type=content_type,
        )
    else:
        # Return the raw content if not a valid stream or an error occurred
        return (
            backend_response.content,
            backend_response.status_code,
            backend_response.headers.items(),
        )


@app.route("/blobstream", methods=["POST"])
def stream_handler_post() -> FlaskResponse:
    """
    Proxy stream handler for POST requests, encrypt and stream a blob to the Azure server.
    Returns

    Proxied_request and standard response are not used here,
    as this function is specifically designed to handle streaming of blobs
    without loading the entire content into memory.

    -------
    FlaskResponse
        A Flask response object containing if the blob was successfully streamed to the server.
    """
    log.debug("Proxy stream POST handler called")

    client: NodeClient = app.config.get("SERVER_IO")
    pubkey_base64 = request.headers.get("X-Public-Key")
    if not pubkey_base64:
        log.error("Missing X-Public-Key header in request.")
        return {"msg": "Missing X-Public-Key header"}, HTTPStatus.BAD_REQUEST

    log.debug("Received public key: %s", pubkey_base64)

    headers = {}
    for h in ["Authorization", "Content-Type", "Content-Length"]:
        if h in request.headers:
            headers[h] = request.headers[h]

    url = f"{server_url}/blobstream"
    log.debug("Making proxied POST request to %s", url)

    encrypted_stream = client.cryptor.encrypt_stream(request.stream, pubkey_base64)
    # Stream the data to the server while encrypting it.
    # This is done to avoid loading the entire content into memory.
    # The encrypted stream is a generator that yields chunks of encrypted data.
    backend_response = requests.post(
        url, params=request.args, headers=headers, data=encrypted_stream
    )

    log.debug("Received response with status code %s", backend_response.status_code)

    if backend_response.status_code > 210:
        log.warning(
            "Proxy server received status code %s", backend_response.status_code
        )
        try:
            log.warning("Error messages: %s", backend_response.json())
        except Exception:
            log.warning("Could not decode error response as JSON.")
        log.debug(
            "method: %s, url: %s, params: %s, headers: %s",
            request.method,
            url,
            request.args,
            headers,
        )
        return (
            backend_response.content,
            backend_response.status_code,
            dict(backend_response.headers),
        )
    return FlaskResponse(
        backend_response.content,
        status=backend_response.status_code,
        headers=dict(backend_response.headers),
    )


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
