"""
Tests that the outside-Flask database session is released.

Covers two things:

- ``DatabaseSessionManager.session_scope`` clears the session both when its body
  exits normally and when the body raises.
- Constructing an ``AlgorithmStoreApp`` leaves no session behind. Startup loads
  the permission rules and syncs the policies outside a Flask request, so the
  request hooks that normally clear the session never fire; a session left here
  keeps its pooled connection in an open transaction for the lifetime of the
  process.
"""

import os
from unittest import TestCase
from unittest.mock import patch

from vantage6.common.globals import InstanceType

from vantage6.backend.common import session as session_module, test_context

from tests_store.base.unittest_base import MOCK_PUBLIC_KEY_PEM
from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.globals import PACKAGE_FOLDER
from vantage6.algorithm.store.model.base import Database, DatabaseSessionManager


class TestSessionScope(TestCase):
    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    def tearDown(self):
        # make sure a failing test does not leak a session into the next one
        DatabaseSessionManager.clear_session()

    def test_session_released_on_normal_exit(self):
        """The outside-Flask session is cleared when the scope exits normally."""
        with DatabaseSessionManager.session_scope() as scoped_session:
            self.assertIsNotNone(scoped_session)
            self.assertIsNotNone(session_module.session)
        self.assertIsNone(session_module.session)

    def test_session_released_when_body_raises(self):
        """The session is cleared even when the body raises - the actual bug."""
        with self.assertRaises(RuntimeError), DatabaseSessionManager.session_scope():
            self.assertIsNotNone(session_module.session)
            raise RuntimeError("work blew up mid-scope")
        self.assertIsNone(session_module.session)


class TestStartupReleasesSession(TestCase):
    """
    Building the app must not leave a session (and connection) checked out.

    Startup loads the permission rules and syncs the policies against the
    database, all outside a Flask request.
    """

    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    def test_no_session_left_after_app_construction(self):
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

        DatabaseSessionManager.clear_session()
        self.assertIsNone(session_module.session)

        with patch(
            "vantage6.algorithm.store.AlgorithmStoreApp._get_keycloak_public_key"
        ) as mock_get_key:
            mock_get_key.return_value = MOCK_PUBLIC_KEY_PEM.decode()
            AlgorithmStoreApp(ctx)

        self.assertIsNone(session_module.session)
