import unittest
import yaml

from vantage6.common.globals import APPNAME, InstanceType
from vantage6.backend.common import test_context
from vantage6.algorithm.store.model.base import Database, DatabaseSessionManager
from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.globals import PACKAGE_FOLDER


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
        # unset session.session
        DatabaseSessionManager.clear_session()
