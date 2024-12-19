import unittest
from vantage6.algorithm.store.default_roles import get_default_roles
from vantage6.algorithm.store.model.review import Review

from vantage6.common.globals import InstanceType, Ports
from vantage6.backend.common import test_context
from vantage6.algorithm.store.model.base import DatabaseSessionManager, Database
from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.globals import PACKAGE_FOLDER
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server


class TestResources(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Called immediately before running a test method."""
        Database().connect("sqlite://", allow_drop_all=True)

        ctx = test_context.TestContext.from_external_config_file(
            PACKAGE_FOLDER, InstanceType.ALGORITHM_STORE
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
        [s.delete() for s in Vantage6Server.get()]
        [u.delete() for u in User.get()]
        [r.delete() for r in Role.get()]
        [r.delete() for r in Review.get()]

        # unset session.session
        DatabaseSessionManager.clear_session()

    def register_server(
        self, server_url: str = f"http://localhost:{Ports.DEV_SERVER.value}"
    ) -> Vantage6Server:
        server = Vantage6Server(url=server_url)
        server.save()
        return server

    def register_user(
        self,
        server_id: int,
        username: str = "test_user",
        user_roles: list[Role] = None,
        user_rules: list[Rule] = None,
        organization_id: int = 1,
    ) -> User:
        user = User(
            username=username, v6_server_id=server_id, organization_id=organization_id
        )
        if user_roles and len(user_roles) > 0:
            user.roles = user_roles
        if user_rules and len(user_rules) > 0:
            user.rules = user_rules
        user.save()
        return user

    def register_user_and_server(
        self,
        username: str = "test_user",
        server_url: str = f"http://localhost:{Ports.DEV_SERVER.value}",
        user_roles: list[Role] = None,
        user_rules: list[Rule] = None,
    ) -> tuple[User, Vantage6Server]:
        server = self.register_server(server_url)
        user = self.register_user(server.id, username, user_roles, user_rules)

        return user, server

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


class MockResponse:
    def __init__(self, json_data=None, status_code=200):
        if json_data is None:
            json_data = {}
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data
