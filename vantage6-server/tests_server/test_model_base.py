import yaml

from unittest import TestCase

from vantage6.server.controller.fixture import load
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.globals import PACKAGE_FOLDER, APPNAME


class TestModelBase(TestCase):

    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

        # FIXME: move path generation to a function in vantage6.server
        file_ = str(
            PACKAGE_FOLDER / APPNAME / "server" / "_data" / "unittest_fixtures.yaml"
        )
        with open(file_) as f:
            cls.entities = yaml.safe_load(f.read())
        load(cls.entities)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()

    def setUp(self):
        DatabaseSessionManager.get_session()

    def tearDown(self):
        DatabaseSessionManager.clear_session()
