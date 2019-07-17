# app.run is only for development
import requests
import os

from flask import Flask, request
from joey.node.server_io import ClientNodeProtocol

from gevent.pywsgi import WSGIServer

app = Flask(__name__)

def server_info():
    """Retrieves environment variables set by the node.
    """
    url = os.environ("SERVER_URL")
    port = os.environ("SERVER_PORT")
    path = os.environ("SERVER_PATH")
    
    assert url, "url not set in the environment variable"
    assert port, "port not set in the environment variable"
    assert path, "path not set in the environment variable"
    return f"{url}{port}{path}"

def rest_method(method):
    return {
        'get': requests.get,
        'post': requests.post,
        'put': requests.put,
        'patch': requests.patch,
        'delete': requests.delete
    }.get(method.lower(), 'get')

@app.route('/')
def info():
    return 'Hello, this is a proxy server'

@app.route('/proxyme')
def proxy():
    """ 
    {
        "method": "POST",
        "endpoint": "/task/...",
        "header": { ... }
        "body": { ... }
    }
    """
    data = request.get_json()
    
    method = data.get("method")
    endpoint = data.get("endpoint")
    headers = data.get("header")
    params = data.get("params",None)
    json_body = data.get("json_body")
    
    call = rest_method(method)
    full_server_url = server_info()
    
    return call(
        full_server_url+endpoint, 
        json=json_body, 
        headers=headers,
        params=params
    )

@app.route("/encrypt")
def encrypt():
    return request.get_json()

@app.route("/decrypt")
def decrypt():
    return request.get_json()


http_server = WSGIServer(('', 5001), app)
http_server.serve_forever()