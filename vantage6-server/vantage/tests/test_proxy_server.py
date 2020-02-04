import logging
import unittest
import yaml
import bcrypt
import datetime
import os
import threading
import multiprocessing

from flask.testing import FlaskClient
from flask import Flask, Response as BaseResponse, json
from werkzeug.utils import cached_property

from vantage.node.proxy_server import app
from vantage import server
from vantage.node.server_io import ClientBaseProtocol
from vantage.node.encryption import Cryptor

from vantage.constants import PACAKAGE_FOLDER, APPNAME, DATA_FOLDER, VERSION
from vantage.util import (
    unpack_bytes_from_transport, 
    prepare_bytes_for_transport
)


log = logging.getLogger(__name__.split(".")[-1])
log.level = logging.DEBUG


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)

class TestCentralServer(FlaskClient):
    def open(self, *args, **kwargs):
        if 'json' in kwargs:
            kwargs['data'] = json.dumps(kwargs.pop('json'))
            kwargs['content_type'] = 'application/json'
        return super().open(*args, **kwargs)

def test_central_server(): # pragma: no cover
    from vantage import util
    from vantage.server.model.base import Database
    from vantage.server.controller.fixture import load

    Database().connect("sqlite://")
    
    file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
    with open(file_) as f:
        entities = yaml.safe_load(f.read())
    load(entities, drop_all=True)
    
    server.app.secret_key = "test-secret"

    ctx = util.TestContext.from_external_config_file(
        "unittest_config.yaml"           
    )
    server.init_resources(ctx)
    ip = '127.0.0.1'
    port = 5000
    
    server.run(ctx=ctx, host=ip, port=port, debug=False)
    
class TestProxyServer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.server = multiprocessing.Process(
            target=test_central_server
        )
        cls.server.start()
        import time
        print("sleeping")
        time.sleep(5)

    def setUp(self):
        # start local server
        
        # self.server = threading.Thread(
        #     target=self.__test_central_server,
        #     daemon=True
        # ).start()

        # set the place where it needs to go to
        os.environ["SERVER_URL"] = "http://127.0.0.1"
        os.environ["SERVER_PORT"] = "5000"
        os.environ["SERVER_PATH"] = "/api"

        # import requests
        # print(requests.get("http://localhost:5000/api/version"))
        # print(requests.get("http://127.0.0.1:5000/api/version"))

        # load encryption module
        server_io = ClientBaseProtocol(
            "127.0.0.1", 5000
        )
        server_io.cryptor = Cryptor(
            DATA_FOLDER / "private_key.pem"
        )
        
        # attach proxy to this local service
        app.testing = True
        app.response_class = Response
        app.test_client_class = TestCentralServer
        app.secret_key = "super-secret!"
        app.config["SERVER_IO"] = server_io
        self.app = app.test_client()

        self.credentials = {
            "root":{
                "username": "root",
                "password": "password"
            },
            "admin":{
                "username": "frank@iknl.nl",
                "password": "password"
            },
            "user":{
                "username": "melle@iknl.nl",
                "password": "password"
            }
        }
        
        self.headers = None
    
    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()

    def login(self, type_='root'):
        
        tokens = self.app.post(
            'token/user',
            json=self.credentials[type_]
        ).get_json()
        
        headers = {
            'Authorization': 'Bearer {}'.format(tokens['access_token'])
        }
        self.headers = headers

    def test_version(self):
        proxy_version = self.app.get("version").get_json()
        self.assertEqual(
            proxy_version.get("version"),
            VERSION
        )

    def test_login(self):
        if not self.headers:
            self.login()
        self.assertIn("Authorization", self.headers)
        self.assertIsInstance(self.headers["Authorization"], str)
    
    def test_task(self):
        if not self.headers:
            self.login()

        input_ = prepare_bytes_for_transport("bla".encode("ascii"))
        proxy_test = self.app.post(
            "task", 
            headers=self.headers,
            json={
                "organizations":[{
                    "id":1,
                    "input":  input_
                }],
                "image": "some-image",
                "collaboration_id": 1
            }
        ).get_json()

        # if we receive results, we assume that all has been returned
        # extensive testing of the API happens in test_resources
        self.assertIn("results", proxy_test)

    def test_result(self):

        if not self.headers:
            self.login()

        proxy_test = self.app.get(
            "result/1", 
            headers=self.headers,
        ).get_json()

        # if we receive input, we assume that all has been returned
        # extensive testing of the API happens in test_resources
        self.assertIn("input", proxy_test)


    
    
    

        
