import logging
import unittest
import yaml
import bcrypt
import datetime
import os
import threading

from flask.testing import FlaskClient
from flask import Flask, Response as BaseResponse, json
from werkzeug.utils import cached_property

from joey.node.proxy_server import app
from joey import server

from joey.constants import PACAKAGE_FOLDER, APPNAME, DATA_FOLDER
from joey.util import unpack_bytes_from_transport


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

class TestProxyServer(unittest.TestCase):

    def setUp(self):
        # start local server
        # threading.Thread(
        #     target=self.__test_central_server,
        #     daemon=True
        # ).start()

        # import requests
        # requests.get("http://127.0.0.1:5000/version")

        # # set the place where it needs to go to
        # os.environ["SERVER_URL"] = "http://127.0.0.1"
        # os.environ["SERVER_PORT"] = "5000"
        # os.environ["SERVER_PATH"] = ""
        # # app.config["SERVER_IO"] = 

        # # attach proxy to this local service
        # app.testing = True
        # app.response_class = Response
        # app.test_client_class = TestCentralServer
        # app.secret_key = "super-secret!"
        # self.app = app.test_client()
        pass

    def __test_central_server(self):
        # from joey import util
        # from joey.server.model.base import Database
        # from joey.server.controller.fixture import load

        # Database().connect("sqlite://")
        # file_ = str(PACAKAGE_FOLDER / APPNAME / "_data" / "example_fixtures.yaml")
        # with open(file_) as f:
        #     self.entities = yaml.safe_load(f.read())
        # load(self.entities, drop_all=True)
        
        # server.app.secret_key = "test-secret"

        # ctx = util.TestContext.from_external_config_file(
        #     "unittest_config.yaml"           
        # )
        # server.init_resources(ctx)
        # ip = '127.0.0.1'
        # port = 5000
        # server.run(ctx, ip, port, debug=False)
        # print("done!")
        pass
        
    def tearDown(self):
        pass

    def test_start_proxy(self):
        pass
        # print(self.app.get("/version"))