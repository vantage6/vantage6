"""
Regression tests for issue #2651 (database sessions not released on exception).

Code that runs outside the Flask request lifecycle - e.g. the background worker
threads and application startup - does not benefit from the request hooks that
normally clear the database session. Without an explicit guard, an exception
raised while a session is in use leaves that session (and its pooled database
connection) dangling, eventually exhausting the connection pool.
``session_scope`` guarantees the session is released, and the connection pool is
only sized for non-SQLite databases.
"""

import os
from unittest import TestCase
from unittest.mock import MagicMock, patch

from flask_socketio import SocketIO
from sqlalchemy.engine.url import make_url

from vantage6.common.globals import InstanceType

from vantage6.backend.common import session as session_module
from vantage6.backend.common.test_context import TestContext

from vantage6.hq import HQApp
from vantage6.hq.globals import PACKAGE_FOLDER
from vantage6.hq.model.base import Database, DatabaseSessionManager


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
        with self.assertRaises(RuntimeError):
            with DatabaseSessionManager.session_scope():
                self.assertIsNotNone(session_module.session)
                raise RuntimeError("work blew up mid-scope")
        self.assertIsNone(session_module.session)


class TestStartupReleasesSession(TestCase):
    """
    Building the app must not leave a session (and connection) checked out.

    The permission manager reads and writes Rule/Role rows while loading the
    rules from the API resources. That happens outside a Flask request, so
    without a session scope the session - and the pooled connection behind it,
    stuck in an open transaction - is held for the lifetime of the process.
    """

    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    def test_no_session_left_after_app_construction(self):
        ctx = TestContext.from_external_config_file(PACKAGE_FOLDER, InstanceType.HQ)

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

        with (
            patch("vantage6.hq.HQApp._get_keycloak_public_key") as mock_get_key,
            patch.object(SocketIO, "start_background_task") as mock_background_task,
            patch("vantage6.hq.Metrics", MagicMock()),
        ):
            mock_get_key.return_value = "dummy-public-key"
            mock_background_task.return_value = None
            HQApp(ctx)

        self.assertIsNone(session_module.session)


class TestBuildEngineKwargs(TestCase):
    def test_sqlite_ignores_pool_settings(self):
        """Pool settings must never reach a SQLite engine (would raise)."""
        url = make_url("sqlite:////tmp/test.db")
        kwargs = Database._build_engine_kwargs(url, pool_size=5, max_overflow=10)
        self.assertEqual(kwargs, {"pool_pre_ping": True})

    def test_postgres_includes_pool_settings_when_set(self):
        url = make_url("postgresql://user:pw@localhost:5432/db")
        kwargs = Database._build_engine_kwargs(url, pool_size=5, max_overflow=10)
        self.assertTrue(kwargs["pool_pre_ping"])
        self.assertEqual(kwargs["pool_size"], 5)
        self.assertEqual(kwargs["max_overflow"], 10)

    def test_postgres_omits_pool_settings_when_none(self):
        """Unset pool settings fall back to SQLAlchemy's own defaults."""
        url = make_url("postgresql://user:pw@localhost:5432/db")
        kwargs = Database._build_engine_kwargs(url, pool_size=None, max_overflow=None)
        self.assertEqual(kwargs, {"pool_pre_ping": True})
