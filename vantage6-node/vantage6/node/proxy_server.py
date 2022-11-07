import concurrent.futures
import requests
import logging

from http import HTTPStatus
from requests import Response
from typing import Callable

from flask import Flask, request, jsonify, copy_current_request_context

from vantage6.node.server_io import NodeClient
from vantage6.node.util import (
    logger_name,
    base64s_to_bytes,
    bytes_to_base64s
)

# Initialize FLASK
app = Flask(__name__)
log = logging.getLogger(logger_name(__name__))

# Need to be set when the proxy server is initialized
app.config["SERVER_IO"] = None
server_url = None

# Number of times the request is retried before the proxy server gives up
RETRY = 3


def get_method(method: str) -> Callable:
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

    loopup = {
        "get": requests.get,
        "post": requests.post,
        "patch": requests.patch,
        "put": requests.put,
        "delete": requests.delete
    }

    return loopup.get(method_name, requests.get)


def make_proxied_request(endpoint: str) -> Response:
    """
    Helper to create proxies requests to the central server.

    Parameters
    ----------
    endpoint: str
        endpoint to be reached at the vantage6-server

    Returns
    -------
    flask.Response
        Response from the vantage6-server
    """
    present = 'Authorization' in request.headers
    headers = {'Authorization': request.headers['Authorization']} if present \
        else None

    return make_request(request.method, endpoint, request.get_json(),
                        request.args, headers)


def make_request(method: str, endpoint: str, json: dict = None,
                 params: dict = None, headers: dict = None) -> Response:
    """
    Make request to the central server

    Parameters
    ----------
    method : str
        HTTP method to be used
    endpoint : str
        endpoint of the vantage6-server
    json : dict, optional
        JSON body, by default None
    params : dict, optional
        HTTP parameters, by default None
    headers : dict, optional
        HTTP headers, by default None

    Returns
    -------
    Response
        Response from the vantage6-server
    """

    method = get_method(method)

    # Forward the request to the central server. Retry when an exception is
    # raised (e.g. timeout or connection error) or when the server gives an
    # error code greater than 210
    url = f"{server_url}/{endpoint}"
    for i in range(RETRY):
        try:
            response: Response = method(url, json=json,
                                        params=params,
                                        headers=headers)
            # verify that the server gave us a valid response, else we
            # would want to try again
            if response.status_code > 210:
                log.warn('Proxy server received status code:'
                         f'{response.status_code}')
                log.debug(f'method: {request.method}, url: {url}, json: {json}, params: {params}, '
                          f'headers: {headers}')
                if 'application/json' in response.headers.get('Content-Type'):
                    log.debug(response.json().get("msg", "no description..."))

            else:
                # Exit the retry loop because we have collected a valid
                # response
                return response

        except Exception:
            log.exception(f'On attempt {i}, the proxy request raised an '
                          f'exception: <{url}>')

    # if all attemps fail, raise an exception to be handled by its parent
    raise Exception("Proxy request failed")


def decrypt_result(result: dict) -> dict:
    """
    Decrypt the `result` from a result dictonary

    Parameters
    ----------
    result : dict
        Result dict

    Returns
    -------
    dict
        Result dict with the `result` decrypted
    """
    server_io: NodeClient = app.config.get('SERVER_IO')

    # if the result is a None, there is no need to decrypt that..
    try:
        if result['result']:
            result["result"] = bytes_to_base64s(
                server_io.cryptor.decrypt_str_to_bytes(
                    result["result"]
                )
            )
    except Exception:
        log.exception("Unable to decrypt and/or decode results, sending them "
                      "to the algorithm...")

    return result


def get_response_json_and_handle_exceptions(response: Response):
    """
    Obtain json content from request response

    Parameters
    ----------
    response : Response
        Requests response object

    Returns
    -------
    dict or None
        Dict containing the json body
    """
    try:
        return response.json()
    except (requests.exceptions.JSONDecodeError, Exception):
        log.exception('Failed to extract JSON')
    return None


@app.route("/task", methods=["POST"])
def proxy_task():
    """
    Proxy to create tasks at the vantage6 server

    Returns
    -------
    flask.Response
        Response from the vantage6-server
    """
    # We need the server io for the decryption of the results
    server_io: NodeClient = app.config.get("SERVER_IO")
    if not server_io:
        log.error("Task proxy request received but proxy server was not "
                  "initialized properly.")
        return jsonify({'msg': 'Proxy server not initialized properly'}), 500

    # All requests from algorithms are unencrypted. We encrypt the input
    # field for a specific organization(s) specified by the algorithm
    data = request.get_json()
    organizations = data.get("organizations")

    if not organizations:
        log.error("No organizations found in proxy request..")
        return jsonify({"msg": "Organizations missing from input"}), 400

    try:
        headers = {'Authorization': request.headers['Authorization']}
    except Exception:
        log.exception('Could not extract headers from request...')

    log.debug(f"{len(organizations)} organizations")

    # For every organization we need to encrypt the input field. This is done
    # in parallel as the client (algorithm) is waiting for a timely response.
    # For every organizationn the public key is retrieved an the input is
    # encrypted specifically for them.
    # @copy_current_request_context
    def encrypt_input(organization: dict) -> dict:
        """
        Encrypt the input for a specific organization by using its private key.
        This method is run as background

        Parameters
        ----------
        organization : dict
            Input as specified by the client (algorithm in this case)

        Returns
        -------
        dict
            Modified organization dictionary in which the `input` key is
            contains encrypted input
        """
        input_ = organization.get("input", {})
        organization_id = organization.get("id")

        # retrieve public key of the organization
        log.debug(f"Retrieving public key of org: {organization_id}")
        response = make_request('get', f'organization/{organization_id}',
                                headers=headers)
        public_key = response.json().get("public_key")

        # Encrypt the input field
        server_io: NodeClient = app.config.get("SERVER_IO")
        organization["input"] = server_io.cryptor.encrypt_bytes_to_str(
            base64s_to_bytes(input_),
            public_key
        )

        log.debug("Input succesfully encrypted for organization "
                f"{organization_id}!")
        return organization

    if server_io.is_encrypted_collaboration():

        log.debug("Applying end-to-end encryption")
        data["organizations"] = [encrypt_input(o) for o in organizations]

        # with concurrent.futures.ThreadPoolExecutor() as executor:
        #     futures = [executor.submit(encrypt_input, o)
        #             for o in organizations]
        # data["organizations"] = [future.result() for future in futures]

    # Attempt to send the task to the central server
    try:
        response = make_request('post', 'task', data, headers=headers)
    except Exception:
        log.exception('post task failed')
        return {'msg': 'Request failed, see node logs'},\
            HTTPStatus.INTERNAL_SERVER_ERROR

    return response.json(), HTTPStatus.OK


@app.route('/task/<int:id>/result', methods=["GET"])
def proxy_task_result(id: int) -> Response:
    """
    Obtain and decrypt all results to belong to a certain task

    Parameters
    ----------
    id : int
        Task id from which the results need to be obtained

    Returns
    -------
    Response
        Reponse from the vantage6-server
    """
    # We need the server io for the decryption of the results
    server_io = app.config.get("SERVER_IO")
    if not server_io:
        return jsonify({'msg': 'Proxy server not initialized properly'}),\
            HTTPStatus.INTERNAL_SERVER_ERROR

    # Forward the request
    try:
        response: Response = make_proxied_request(f"task/{id}/result")
    except Exception:
        log.exception('Error on /result/<int:id>')
        return {'msg': 'Request failed, see node logs'},\
            HTTPStatus.INTERNAL_SERVER_ERROR

    # Attempt to decrypt the results. The enpoint should have returned
    # a list of results
    unencrypted = []
    results = get_response_json_and_handle_exceptions(response)
    for result in results:
        result = decrypt_result(result)
        unencrypted.append(result)

    return jsonify(unencrypted), HTTPStatus.OK


@app.route('/result/<int:id>', methods=["GET"])
def proxy_results(id: int) -> Response:
    """
    Obtain and decrypt the result from the vantage6 server to be used by
    an algorithm container.

    Parameters
    ----------
    id : int
        Id of the result to be obtained

    Returns
    -------
    flask.Response
        Response of the vantage6-server
    """
    # We need the server io for the decryption of the results
    server_io: NodeClient = app.config.get("SERVER_IO")
    if not server_io:
        return {'msg': 'Proxy server not initialized properly'},\
            HTTPStatus.INTERNAL_SERVER_ERROR

    # Make the proxied request
    try:
        response: Response = make_proxied_request(f"result/{id}")
    except Exception:
        log.exception('Error on /result/<int:id>')
        return {'msg': 'Request failed, see node logs...'},\
            HTTPStatus.INTERNAL_SERVER_ERROR

    # Try to decrypt the results
    result = get_response_json_and_handle_exceptions(response)
    result = decrypt_result(result)

    return result, HTTPStatus.OK


@app.route('/<path:central_server_path>', methods=["GET", "POST", "PATCH",
                                                   "PUT", "DELETE"])
def proxy(central_server_path: str) -> Response:
    """
    Generalized http proxy request

    Parameters
    ----------
    central_server_path : str
        The endpoint on the server to be reached

    Returns
    -------
    flask.Response
        Contains the server response
    """
    try:
        response = make_proxied_request(central_server_path)
    except Exception:
        log.exception('Generic proxy endpoint')
        return {'msg': 'Request failed, see node logs'},\
            HTTPStatus.INTERNAL_SERVER_ERROR

    return response.content, response.status_code, response.headers.items()
