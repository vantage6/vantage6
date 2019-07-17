"""Proxy the communication from the algorithm to the central server.

This module creates a tiny Flask app, to which the algorithm containers
can make central server requests. Thereby limiting the connectivity of 
the algorithm containers.

Example:
    

Attributes: 
    app (FlaskApp): contains the flask application

Todo:
    * bearer token from the node needs to be inserted
    * limit the endpoints a container can reach, maybe add a arg and
        check for it at the server
    * encrypt input and result field
    
"""
import requests
import os

from flask import Flask, request, jsonify
from joey.node.server_io import ClientNodeProtocol

app = Flask(__name__)

def server_info():
    """Retrieves environment variables set by the node."""
    url = os.environ["SERVER_URL"]
    port = os.environ["SERVER_PORT"]
    path = os.environ["SERVER_PATH"]
    return f"{url}:{port}{path}"

@app.route('/<path:central_server_path>')
def proxy(central_server_path):
    """Endpoint that will forward everything to the central server."""
    return jsonify({
        "path":central_server_path, 
        "method":request.method, 
        "args": request.args,
        "body": request.get_json(),
        "headers":dict(request.headers)
    })

@app.route('/test/<path:central_server_path>')
def test(central_server_path):
    """Test endpoint, to be removed."""
    url = server_info()
    response = requests.get(url+"/"+central_server_path)
    return jsonify(response.json())
