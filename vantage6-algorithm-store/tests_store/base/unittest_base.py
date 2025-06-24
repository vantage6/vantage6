import os
import unittest
from unittest.mock import Mock
from http import HTTPStatus

from vantage6.common.globals import InstanceType
from vantage6.backend.common import test_context
from vantage6.algorithm.store.default_roles import get_default_roles
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.base import DatabaseSessionManager, Database
from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.globals import PACKAGE_FOLDER
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User


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
        os.environ["KEYCLOAK_USER_CLIENT"] = "dummy-keycloak-user-client"
        os.environ["KEYCLOAK_USER_CLIENT_SECRET"] = "dummy-keycloak-user-client-secret"
        os.environ["KEYCLOAK_ADMIN_CLIENT"] = "dummy-keycloak-admin-client"
        os.environ["KEYCLOAK_ADMIN_CLIENT_SECRET"] = (
            "dummy-keycloak-admin-client-secret"
        )

        cls.server = AlgorithmStoreApp(ctx)
        cls.server.app.testing = True
        cls.app = cls.server.app.test_client()

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    @classmethod
    def setUp(cls):
        # set session.session
        DatabaseSessionManager.get_session()

    @classmethod
    def tearDown(cls):
        # delete resources from database
        # pylint: disable=expression-not-assigned
        [p.delete() for p in Policy.get()]
        [u.delete() for u in User.get()]
        [r.delete() for r in Role.get()]
        [r.delete() for r in Review.get()]

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
