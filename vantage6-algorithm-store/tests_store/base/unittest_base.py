import unittest
import yaml

from vantage6.common.globals import APPNAME, InstanceType
from vantage6.backend.common import test_context
from vantage6.algorithm.store.model.base import Database, DatabaseSessionManager
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

        # create server instance. Patch the start_background_task method
        # to prevent the server from starting a ping/pong thread that will
        # prevent the tests from starting
        store_app = AlgorithmStoreApp(ctx)
        cls.server = store_app

        # file_ = str(
        #     PACKAGE_FOLDER / APPNAME / "server" / "_data" / "unittest_fixtures.yaml"
        # )
        # with open(file_) as f:
        #     cls.entities = yaml.safe_load(f.read())
        # load(cls.entities)

        store_app.app.testing = True
        cls.app = store_app.app.test_client()

        cls.credentials = {
            "root": {"username": "root", "password": "root"},
        }

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

        # unset session.session
        DatabaseSessionManager.clear_session()

    def register_server(
        self, server_url: str = "http://localhost:5000"
    ) -> Vantage6Server:
        server = Vantage6Server(url=server_url)
        server.save()
        return server

    def register_user(self, server_id: int, username: str = "test_user") -> User:
        user = User(username=username, v6_server_id=server_id)
        user.save()
        return user

    def register_user_and_server(
        self, username: str = "test_user", server_url: str = "http://localhost:5000"
    ) -> tuple[User, Vantage6Server]:
        server = self.register_server(server_url)
        user = self.register_user(server.id, username)
        return user, server

    def create_role(self, rules: list[Rule], name: str = "test_role") -> Role:
        role = Role(name=name, rules=rules)
        role.save()
        return role

    def assign_role_to_user(self, user: User, role: Role):
        user.roles.append(role)
        user.save()


class MockResponse:
    def __init__(self, json_data={}, status_code=200):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data
