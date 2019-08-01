"""Proxy the communication from the algorithm to the central server.

This module creates a tiny Flask app, to which the algorithm containers
can make central server requests. Thereby limiting the connectivity of 
the algorithm containers.

Example:
    

Attributes: 
    app (FlaskApp): contains the flask application

Todo:
    * encrypt input and result field

"""
import requests
import os
import logging

from flask import Flask, request, jsonify
from joey.node.server_io import ClientNodeProtocol
from joey.util import logger_name

app = Flask(__name__)

log = logging.getLogger(logger_name(__name__))

def server_info():
    """Retrieves environment variables set by the node."""
    url = os.environ["SERVER_URL"]
    port = os.environ["SERVER_PORT"]
    path = os.environ["SERVER_PATH"]
    return f"{url}:{port}{path}"

@app.route("/task", methods=["POST"])
def proxy_task():
    """Create new task at the server instance"""
    
    url = server_info()
    
    auth = request.headers['Authorization']
    log.debug(f"container token = {auth}")
    
    try:
        response = requests.post(
            f"{url}/task",
            headers={'Authorization': auth},
            json=request.get_json()
        )

    except Exception as e:
        log.error("Proxyserver was unable to retreive results...")
        log.debug(e)

    return jsonify(response.json())

@app.route('/result/<int:id>', methods=["GET"])
def proxy_results(id):
    """Obtain results from the server"""
    
    url = server_info()

    auth = request.headers['Authorization']
    
    try:
        response = requests.get(
            f"{url}/result/{id}",
            headers={'Authorization': auth}
        )
    except Exception as e:
        log.error("Proxyserver was unable to retreive results...")
        log.debug(e)

    return jsonify(response.json())

@app.route('/<path:central_server_path>')
def proxy(central_server_path):
    """Endpoint that will forward everything to the central server."""
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
    auth = request.headers['Authorization']
    auth_found = bool(auth)
    log.debug(f"method = {method_name}, auth = {auth_found}")
    
    try:
        response = method(
            f"{url}/{central_server_path}",
            json=request.get_json(),
            params=request.args,
            headers={'Authorization': auth}
        )
    except Exception as e:
        log.error("Proxyserver was unable to retreive endpoint...")
        log.debug(e)
    
    if response.status_code > 200:
        log.error(f"server response code {response.status_code}")
        log.debug(response.json().get("msg","no description..."))
    
    return jsonify(response.json())

@app.route('/test/<path:central_server_path>')
def test(central_server_path):
    """Test endpoint, to be removed."""
    url = server_info()
    response = requests.get(url+"/"+central_server_path)
    return jsonify(response.json())
