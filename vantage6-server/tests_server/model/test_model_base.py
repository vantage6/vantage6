from unittest import TestCase

from vantage6.server.model.base import Database, DatabaseSessionManager


class TestModelBase(TestCase):
    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    def setUp(self):
        DatabaseSessionManager.get_session()

    def tearDown(self):
        DatabaseSessionManager.clear_session()
