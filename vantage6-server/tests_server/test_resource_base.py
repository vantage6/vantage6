from uuid import uuid1
import unittest
import random
import string
import yaml
import json

from http import HTTPStatus

from flask import Response as BaseResponse
from flask.testing import FlaskClient
from flask_socketio import SocketIO
from werkzeug.utils import cached_property

from vantage6.backend.common.test_context import TestContext
from vantage6.server.globals import PACKAGE_FOLDER

from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.common.globals import APPNAME, InstanceType
from vantage6.common.enum import RunStatus
from vantage6.server.controller.fixture import load
from vantage6.server import ServerApp
from vantage6.server.model import (
    Organization,
    User,
    Node,
    Collaboration,
    Task,
    Run,
)

from unittest.mock import patch


class Response(BaseResponse):
    @cached_property
    def json(self):
        return json.loads(self.data)


class TestNode(FlaskClient):
    def open(self, *args, **kwargs):
        if "json" in kwargs:
            kwargs["data"] = json.dumps(kwargs.pop("json"))
            kwargs["content_type"] = "application/json"
        return super().open(*args, **kwargs)


class TestResourceBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Called immediately before running a test method."""
        Database().connect("sqlite://", allow_drop_all=True)

        ctx = TestContext.from_external_config_file(PACKAGE_FOLDER, InstanceType.SERVER)

        # create server instance. Patch the start_background_task method
        # to prevent the server from starting a ping/pong thread that will
        # prevent the tests from starting
        with patch.object(SocketIO, "start_background_task"):
            server = ServerApp(ctx)
        cls.server = server

        file_ = str(
            PACKAGE_FOLDER / APPNAME / "server" / "_data" / "unittest_fixtures.yaml"
        )
        with open(file_) as f:
            cls.entities = yaml.safe_load(f.read())
        load(cls.entities)

        server.app.testing = True
        cls.app = server.app.test_client()

        cls.credentials = {
            "root": {"username": "root", "password": "root"},
            "admin": {"username": "frank-iknl", "password": "password"},
            "user": {"username": "melle-iknl", "password": "password"},
            "user-to-delete": {"username": "dont-use-me", "password": "password"},
        }

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    def setUp(self):
        # set session.session
        DatabaseSessionManager.get_session()

    def tearDown(self):
        # unset session.session
        DatabaseSessionManager.clear_session()

    def login(self, type_="root"):
        with self.server.app.test_client() as client:
            tokens = client.post("/api/token/user", json=self.credentials[type_]).json
        if "access_token" in tokens:
            headers = {"Authorization": "Bearer {}".format(tokens["access_token"])}
            return headers
        else:
            print("something wrong, during login:")
            print(tokens)
            return None

    def create_user(self, organization=None, rules=None, password="password"):
        if not rules:
            rules = []
        if not organization:
            organization = Organization(name=str(uuid1()))
            organization.save()

        # user details
        username = random.choice(string.ascii_letters) + str(uuid1())

        # create a temporary organization
        user = User(
            username=username,
            password=password,
            organization=organization,
            email=f"{username}@test.org",
            rules=rules,
        )
        user.save()

        self.credentials[username] = {"username": username, "password": password}

        return user

    def create_node(self, organization=None, collaboration=None):
        if not organization:
            organization = Organization(name=str(uuid1()))

        if not collaboration:
            collaboration = Collaboration(name=str(uuid1()))

        api_key = str(uuid1())
        node = Node(
            name=str(uuid1()),
            api_key=api_key,
            organization=organization,
            collaboration=collaboration,
        )
        node.save()

        return node, api_key

    def login_node(self, api_key):
        tokens = self.app.post("/api/token/node", json={"api_key": api_key}).json
        if "access_token" in tokens:
            headers = {"Authorization": "Bearer {}".format(tokens["access_token"])}
        else:
            print(tokens)

        return headers

    def login_container(
        self, collaboration=None, organization=None, node=None, task=None, api_key=None
    ):
        if not node:
            if not collaboration:
                collaboration = Collaboration(name=str(uuid1()))
            if not organization:
                organization = Organization(name=str(uuid1()))
            api_key = str(uuid1())
            node = Node(
                organization=organization, collaboration=collaboration, api_key=api_key
            )
            node.save()
        else:
            collaboration = node.collaboration
            organization = node.organization

        if not task:
            task = Task(
                image="some-image",
                collaboration=collaboration,
                runs=[Run(status=RunStatus.PENDING)],
            )
            task.save()

        headers = self.login_node(api_key)
        tokens = self.app.post(
            "/api/token/container",
            headers=headers,
            json={"image": "some-image", "task_id": task.id},
        ).json

        if "msg" in tokens:
            print(tokens["msg"])

        headers = {"Authorization": "Bearer {}".format(tokens["container_token"])}
        return headers

    def paginated_list(self, url: str, headers: dict = None) -> tuple[Response, list]:
        """
        Get all resources of a list endpoint by browsing through all pages

        Parameters
        ----------
        url: str
            The url of the list endpoint
        headers: dict
            The headers to use for the request
        kwargs: dict
            Additional arguments to pass to the request

        Returns
        -------
        tuple[flask.Response, list]
            The response and the list of all resources
        """
        result = self.app.get(url, headers=headers)

        # check if response is OK
        if result.status_code != HTTPStatus.OK:
            return result, []

        # get data
        links = result.json.get("links")
        page = 1
        json_data = result.json.get("data")
        if json_data is None:
            json_data = []
        while links and links.get("next"):
            page += 1
            new_response = self.app.get(links.get("next"), headers=headers)
            json_data += (
                new_response.json.get("data") if new_response.json.get("data") else []
            )
            links = new_response.json.get("links")
        return result, json_data

    def create_node_and_login(self, *args, **kwargs):
        _, api_key = self.create_node(*args, **kwargs)
        return self.login_node(api_key)

    def get_user_auth_header(self, organization=None, rules=None):
        if rules is None:
            rules = []
        user = self.create_user(organization, rules)
        return self.login(user.username)
