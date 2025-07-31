import os
import unittest
from http import HTTPStatus
from unittest.mock import Mock, patch

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from vantage6.common.globals import InstanceType

from vantage6.backend.common import test_context

from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.default_roles import get_default_roles
from vantage6.algorithm.store.globals import PACKAGE_FOLDER
from vantage6.algorithm.store.model.base import Database, DatabaseSessionManager
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User

# Generate a mock RSA key pair for testing
MOCK_PRIVATE_KEY = rsa.generate_private_key(
    public_exponent=65537, key_size=2048, backend=default_backend()
)
MOCK_PUBLIC_KEY = MOCK_PRIVATE_KEY.public_key()
MOCK_PRIVATE_KEY_PEM = MOCK_PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
)
MOCK_PUBLIC_KEY_PEM = MOCK_PUBLIC_KEY.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
)


class TestResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Called immediately before running a test method."""

        Database().connect("sqlite://", allow_drop_all=True)

        ctx = test_context.TestContext.from_external_config_file(
            PACKAGE_FOLDER, InstanceType.ALGORITHM_STORE
        )

        # set required environment variables *before* creating the app
        os.environ["KEYCLOAK_URL"] = "dummy-keycloak-url"
        os.environ["KEYCLOAK_REALM"] = "dummy-keycloak-realm"
        os.environ["KEYCLOAK_ADMIN_USERNAME"] = "dummy-keycloak-admin-username"
        os.environ["KEYCLOAK_ADMIN_PASSWORD"] = "dummy-keycloak-admin-password"
        os.environ["KEYCLOAK_ADMIN_CLIENT"] = "dummy-keycloak-admin-client"
        os.environ["KEYCLOAK_ADMIN_CLIENT_SECRET"] = (
            "dummy-keycloak-admin-client-secret"
        )

        # Mock the Keycloak public key fetch
        with patch(
            "vantage6.algorithm.store.AlgorithmStoreApp._get_keycloak_public_key"
        ) as mock_get_key:
            mock_get_key.return_value = MOCK_PUBLIC_KEY_PEM.decode()
            # create server instance. Patch the start_background_task method
            # to prevent the server from starting a ping/pong thread that will
            # prevent the tests from starting
            server = AlgorithmStoreApp(ctx)
            # Configure JWT for container tokens
            server.app.config["JWT_PRIVATE_KEY"] = MOCK_PRIVATE_KEY_PEM
            server.app.config["JWT_PUBLIC_KEY"] = MOCK_PUBLIC_KEY_PEM

        cls.server = server
        cls.server.app.testing = True
        cls.app = cls.server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    @classmethod
    def setUp(cls):
        # set session.session
        DatabaseSessionManager.get_session()

    @classmethod
    def tearDown(cls):
        # delete resources from database
        policies_to_delete = Policy.get()
        for p in policies_to_delete:
            p.delete()
        users_to_delete = User.get()
        for u in users_to_delete:
            u.delete()
        roles_to_delete = Role.get()
        for r in roles_to_delete:
            r.delete()
        reviews_to_delete = Review.get()
        for r in reviews_to_delete:
            r.delete()

        # unset session.session
        DatabaseSessionManager.clear_session()

    def register_user(
        self,
        username: str = "test_user",
        user_roles: list[Role] = None,
        user_rules: list[Rule] = None,
        organization_id: int = 1,
        authenticate_mock: Mock = None,
        auth: bool = True,
    ) -> User:
        user = User(username=username, organization_id=organization_id)
        if user_roles and len(user_roles) > 0:
            user.roles = user_roles
        if user_rules and len(user_rules) > 0:
            user.rules = user_rules
        user.save()
        if authenticate_mock:
            self._mock_auth(user, authenticate_mock, auth)
        return user

    def _mock_auth(self, user: User, authenticate_mock: Mock, auth: bool):
        authenticate_mock.return_value = (
            (user, HTTPStatus.OK)
            if auth
            else ({"msg": "Unauthorized"}, HTTPStatus.UNAUTHORIZED)
        )

    def create_role(self, rules: list[Rule], name: str = "test_role") -> Role:
        role = Role(name=name, rules=rules)
        role.save()
        return role

    def assign_role_to_user(self, user: User, role: Role):
        user.roles.append(role)
        user.save()

    def create_default_roles(self) -> list[Role]:
        for role in get_default_roles():
            new_role = Role(
                name=role["name"],
                description=role["description"],
                rules=role["rules"],
            )
            new_role.save()
