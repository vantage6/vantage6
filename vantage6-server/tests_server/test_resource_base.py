from uuid import uuid1
import unittest
import random
import string
import os
import json
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

from http import HTTPStatus

from flask import Response as BaseResponse
from flask.testing import FlaskClient
from flask_socketio import SocketIO
from werkzeug.utils import cached_property
from unittest.mock import patch

from vantage6.backend.common.test_context import TestContext
from vantage6.server.globals import PACKAGE_FOLDER

from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.common.globals import InstanceType
from vantage6.common.enum import AlgorithmStepType, RunStatus
from vantage6.server import ServerApp
from vantage6.server.model import (
    Organization,
    User,
    Node,
    Collaboration,
    Task,
    Run,
    Rule,
)


# Generate a mock RSA key pair for testing
MOCK_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
MOCK_PUBLIC_KEY = MOCK_PRIVATE_KEY.public_key()

# Convert to PEM format
MOCK_PRIVATE_KEY_PEM = MOCK_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
MOCK_PUBLIC_KEY_PEM = MOCK_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


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

        # set required environment variables *before* creating the app
        os.environ["KEYCLOAK_URL"] = "dummy-keycloak-url"
        os.environ["KEYCLOAK_REALM"] = "dummy-keycloak-realm"
        os.environ["KEYCLOAK_ADMIN_USERNAME"] = "dummy-keycloak-admin-username"
        os.environ["KEYCLOAK_ADMIN_PASSWORD"] = "dummy-keycloak-admin-password"
        os.environ["KEYCLOAK_USER_CLIENT"] = "dummy-keycloak-user-client"
        os.environ["KEYCLOAK_USER_CLIENT_SECRET"] = "dummy-keycloak-user-client-secret"
        os.environ["KEYCLOAK_ADMIN_CLIENT"] = "dummy-keycloak-admin-client"
        os.environ["KEYCLOAK_ADMIN_CLIENT_SECRET"] = (
            "dummy-keycloak-admin-client-secret"
        )

        # Mock the Keycloak public key fetch
        with patch(
            "vantage6.server.ServerApp._get_keycloak_public_key"
        ) as mock_get_key:
            mock_get_key.return_value = MOCK_PUBLIC_KEY_PEM.decode()
            # create server instance. Patch the start_background_task method
            # to prevent the server from starting a ping/pong thread that will
            # prevent the tests from starting
            with patch.object(SocketIO, "start_background_task"):
                server = ServerApp(ctx)
                # Configure JWT for container tokens
                server.app.config["JWT_PRIVATE_KEY"] = MOCK_PRIVATE_KEY_PEM
                server.app.config["JWT_PUBLIC_KEY"] = MOCK_PUBLIC_KEY_PEM
        cls.server = server

        server.app.testing = True
        cls.app = server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    def setUp(self):
        # set session.session
        DatabaseSessionManager.get_session()

    def tearDown(self):
        # unset session.session
        DatabaseSessionManager.clear_session()

    def login(self, user: User | None = None):
        if user is None:
            user = self.create_user()

        # Create a real JWT token with mock claims
        mock_claims = {
            "sub": user.keycloak_id,
            "vantage6_client_type": "user",
            "exp": 9999999999,
            "iat": 0,
        }
        # Sign with the private key
        mock_token = jwt.encode(mock_claims, MOCK_PRIVATE_KEY_PEM, algorithm="RS256")
        return {"Authorization": f"Bearer {mock_token}"}

    def login_as_root(self):
        organization = Organization(name=str(uuid1()))
        organization.save()
        user = User(
            username=str(uuid1()),
            rules=Rule.get(),
            keycloak_id=str(uuid1()),
            organization=organization,
        )
        user.save()
        return self.login(user)

    def create_user(self, organization=None, rules=None):
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
            organization=organization,
            email=f"{username}@test.org",
            rules=rules,
            keycloak_id=str(uuid1()),
        )
        user.save()

        return user

    def create_node(self, organization=None, collaboration=None):
        if not organization:
            organization = Organization(name=str(uuid1()))

        if not collaboration:
            collaboration = Collaboration(name=str(uuid1()))

        node = Node(
            name=str(uuid1()),
            organization=organization,
            collaboration=collaboration,
            keycloak_id=str(uuid1()),
        )
        node.save()

        return node

    def login_node(self, node: Node):
        # Create a real JWT token with mock claims
        mock_claims = {
            "sub": node.keycloak_id,
            "vantage6_client_type": "node",
            "exp": 9999999999,
            "iat": 0,
        }
        # Sign with the private key
        mock_token = jwt.encode(mock_claims, MOCK_PRIVATE_KEY_PEM, algorithm="RS256")
        return {"Authorization": f"Bearer {mock_token}"}

    def login_container(
        self,
        collaboration=None,
        organization=None,
        node=None,
        task=None,
        action: AlgorithmStepType = AlgorithmStepType.CENTRAL_COMPUTE,
    ):
        if not node:
            if not organization:
                organization = Organization(name=str(uuid1()))
            if not collaboration:
                collaboration = Collaboration(
                    name=str(uuid1()), organizations=[organization]
                )
            node = Node(
                organization=organization,
                collaboration=collaboration,
                keycloak_id=str(uuid1()),
            )
            node.save()
        else:
            collaboration = node.collaboration
            organization = node.organization

        if not task:
            task = Task(
                image="some-image",
                collaboration=collaboration,
                runs=[Run(status=RunStatus.PENDING, action=action)],
            )
            task.save()

        headers = self.login_node(node)
        with patch("flask_jwt_extended.get_jwt") as mock_get_token, patch(
            "flask_jwt_extended.get_jwt_identity"
        ) as mock_get_identity:
            mock_get_token.return_value = {
                "sub": node.keycloak_id,
                "vantage6_client_type": "node",
            }
            mock_get_identity.return_value = node.keycloak_id
            token = self.app.post(
                "/api/token/container",
                headers=headers,
                json={"image": "some-image", "task_id": task.id},
            ).json

        if "msg" in token:
            print(token["msg"])

        headers = {"Authorization": "Bearer {}".format(token["container_token"])}
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
        node = self.create_node(*args, **kwargs)
        return self.login_node(node)

    def get_user_auth_header(self, organization=None, rules=None):
        if rules is None:
            rules = []
        user = self.create_user(organization, rules)
        return self.login(user)

    def create_user_and_login(self, organization=None, rules=None):
        user = self.create_user(organization, rules)
        return self.login(user)

    def create_task(self, collaboration=None):
        if not collaboration:
            organization = Organization(name=str(uuid1()))
            collaboration = Collaboration(
                name=str(uuid1()), organizations=[organization]
            )
            collaboration.save()

        task = Task(
            image="some-image",
            collaboration=collaboration,
        )
        task.save()
        return task

    def create_run(self, task=None):
        if not task:
            task = self.create_task()
        run = Run(status=RunStatus.PENDING, task=task)
        run.save()
        return run
