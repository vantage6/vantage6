""" Proxy server

Handles all communication from the node (and algorithm) to the central
server. This module creates a tiny Flask app, to which the algorithm
containers can make requests to the central server. Thereby limiting the
interface of the algorithm containers to the ouside world, as they can
only reach this proxy-server.

Note that the algorithm containers still need to have a JWT
authorization token. This way the server can validate the request of the
algorithm.
"""
import requests
import os
import logging
import json

from flask import Flask, request, jsonify

from vantage6.node.util import (
    logger_name,
    base64s_to_bytes,
    bytes_to_base64s
)
from vantage6.node.server_io import ClientNodeProtocol
from vantage6.client.encryption import CryptorBase, DummyCryptor, RSACryptor

# Setup FLASK
app = Flask(__name__)
log = logging.getLogger(logger_name(__name__))
app.config["SERVER_IO"] = None


def server_info():
    """ Retrieve proxy server details environment variables set by the
        node.
    """
    url = os.environ["SERVER_URL"]
    port = os.environ["SERVER_PORT"]
    path = os.environ["SERVER_PATH"]
    return f"{url}:{port}{path}"


@app.route("/task", methods=["POST"])
def proxy_task():
    """ Create new task at the server instance

        It expect a JSON body containing `input` and `organizations`.
        The `input` is encrypted for the `organizations` using their
        public key. The method expects that the setting SERVER_IO is
        set at the FLASK APP.

        TODO public_key retrieval should happen at node start-up however
            we might need to verify it at a later stage.
        TODO we might want to allow entire collaborations instead of
            only the `organizations`. Thus if the field `organizations`
            is unspecified, we send the message to all participating
            organizations.
        TODO we might not want to use the SERVER_IO, as we only use the
            encryption property of it
        TODO if no public key is present, we should have some sort of
            fallback
    """
    assert app.config["SERVER_IO"], "Server IO not initialized"

    # retrieve URL from local proxy server
    url = server_info()

    # extract the header from the algorithm's request
    auth = request.headers['Authorization']

    # the server IO class will be linked outside this module to the
    # flask app
    server_io = app.config["SERVER_IO"]

    # all requests from algorithms are unencrypted. We encrypt the input
    # field for a specific organization(s) specified by the algorithm
    unencrypted = request.get_json()
    organizations = unencrypted.get("organizations", None)

    if not organizations:
        log.error("No organizations found?!")
        return

    n_organizations = len(organizations)
    log.debug(f"{n_organizations} organizations, attemping to encrypt")
    encrypted_organizations = []

    for organization in organizations:
        input_ = organization.get("input", {})
        if not input_:
            log.error("No input for organization?!")
            return

        organization_id = organization.get("id", None)
        log.debug(f"retreiving public key of org={organization_id}")

        # retrieve public key of the organization
        response = requests.get(
            f"{url}/organization/{organization_id}",
            headers={'Authorization': auth}
        )

        public_key = response.json().get("public_key")

        # Simple JSON (only for unencrypted collaborations)
        # if isinstance(input_, dict):
        #     input_ = bytes_to_base64s(
        #         json.dumps(input_).encode(STRING_ENCODING)
        #     )

        # log.warn('Trying to unpack input:')
        # log.warn(input_)

        input_unpacked = base64s_to_bytes(input_)

        encrypted_input = server_io.cryptor.encrypt_bytes_to_str(
            input_unpacked,
            public_key
        )

        # log.debug(f"should be unreadable={encrypted_input}")
        organization["input"] = encrypted_input
        encrypted_organizations.append(organization)
        log.debug(
            f"Input succesfully encrypted for organization {organization_id}!"
        )

    # attemt to send the task to the central server
    unencrypted["organizations"] = encrypted_organizations
    json_data = unencrypted
    try:
        response = requests.post(
            f"{url}/task",
            headers={'Authorization': auth},
            json=json_data
        )
    except Exception as e:
        log.error("Proxyserver was unable to post new task!")
        log.debug(e)

    return jsonify(response.json())


@app.route('/task/<int:id>/result', methods=["GET"])
def proxy_task_result(id):
    url = server_info()

    server_io = app.config["SERVER_IO"]

    auth = request.headers['Authorization']

    try:
        results = requests.get(
            f"{url}/task/{id}/result",
            headers={'Authorization': auth}
        ).json()

        unencrypted = []
        for result in results:
            if result['result']:
                result["result"] = server_io.cryptor.decrypt_str_to_bytes(
                    result["result"]
                )
                result["result"] = bytes_to_base64s(result["result"])

            unencrypted.append(
                result
            )

        # log.error(unencrypted)

    except Exception as e:
        log.error("Proxyserver was unable to retrieve results (1)!")
        log.debug(e)

    return jsonify(unencrypted)


@app.route('/result/<int:id>', methods=["GET"])
def proxy_results(id):
    """ Obtain result `id` from the server.

        :param id: the id of the result to retrieve

        TODO decrypt the results
    """
    url = server_info()

    server_io = app.config["SERVER_IO"]

    auth = request.headers['Authorization']

    try:
        response = requests.get(
            f"{url}/result/{id}",
            headers={'Authorization': auth}
        )
        encrypted_input = response["result"]
        response["result"] = bytes_to_base64s(
            server_io.cryptor.decrypt_str_to_bytes(
                response["result"]
            )
        )
        # log.error(response)
    except Exception as e:
        log.error("Proxyserver was unable to retrieve results! (2)")
        log.debug(e)

    return jsonify(response.json())


@app.route('/<path:central_server_path>',
           methods=["GET", "POST", "PATCH", "PUT", "DELETE"])
def proxy(central_server_path):
    """ Generic endpoint that will forward everything to the central server.

        :param central_server_path: the endpoint path to call
    """
    log.info(f'Generic proxy request for {central_server_path}')
    url = server_info()

    method_name = request.method.lower()
    method = {
        "get": requests.get,
        "post": requests.post,
        "patch": requests.patch,
        "put": requests.put,
        "delete": requests.delete
    }.get(method_name, requests.get)

    # auth = None
    # if "Authorization" in request.headers:
    try:
        auth = request.headers['Authorization']
        auth_found = True
    except Exception as e:
        log.info("No authorization header found, this could lead to errors")
        auth = None
        auth_found = False

    # log.debug(f"method = {method_name}, auth = {auth_found}")

    api_url = f"{url}/{central_server_path}"
    # print("*************")
    # print(api_url)
    # log.info(f"{method_name} | {api_url}")
    try:
        response = method(
            api_url,
            json=request.get_json(),
            params=request.args,
            headers={'Authorization': auth}
        )
    except Exception as e:
        log.error("Proxyserver was unable to retreive endpoint...")
        print(e)
        log.debug(e)
        return

    if response.status_code > 200:
        log.error(f"server response code {response.status_code}")
        log.debug(response.json().get("msg", "no description..."))

    return jsonify(response.json())
