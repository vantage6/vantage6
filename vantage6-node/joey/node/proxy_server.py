# app.run is only for development
import requests
import os

from flask import Flask, request, jsonify
from joey.node.server_io import ClientNodeProtocol

app = Flask(__name__)

# TODO attach bearer header

def server_info():
    """Retrieves environment variables set by the node.
    """
    url = os.environ["SERVER_URL"]
    port = os.environ["SERVER_PORT"]
    path = os.environ["SERVER_PATH"]
    
    assert url, "url not set in the environment variable"
    # assert port, "port not set in the environment variable"
    # assert path, "path not set in the environment variable"
    return f"{url}:{port}{path}"

@app.route('/')
def info():
    info = server_info()
    return f'Hello, this is a proxy server for server: {info}'

@app.route('/proxy/<path:central_server_path>')
def proxy(central_server_path):
    return jsonify({
        "path":central_server_path, 
        "method":request.method, 
        "args": request.args,
        "body": request.get_json(),
        "headers":dict(request.headers)
    })

@app.route('/test/<path:central_server_path>')
def test(central_server_path):
    url = server_info()
    # return f"{url}/{central_server_path}"
    response = requests.get(url+"/"+central_server_path)
    return jsonify(response.json())
