"""
Tests that WebSocket event handlers release their database session.

WebSocket handlers run inside a Flask request context, and the database session
is cleared by a ``teardown_request`` hook rather than ``after_request``, since
the latter does not fire for socket events and is skipped when a handler raises.
These tests check that the teardown hook clears the session even when a handler
raises, that it is a harmless no-op for handlers that never touch the database,
and that the HQ app actually registers such a hook.
"""

from unittest import TestCase
from unittest.mock import patch

from flask import Flask
from flask_socketio import SocketIO

from vantage6.hq.model import Organization
from vantage6.hq.model.base import Database, DatabaseSessionManager

from .test_resource_base import TestResourceBase


class TestWebsocketSessionCleanup(TestCase):
    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    @staticmethod
    def _build_app():
        """Minimal Flask + SocketIO app with the same teardown hook the backend
        factory registers (backend/common/__init__.py)."""
        app = Flask(__name__)
        app.config["SECRET_KEY"] = "test"

        @app.teardown_request
        def _remove_db_session_on_teardown(exc):
            DatabaseSessionManager.clear_session()

        socketio = SocketIO(app, async_mode="threading")
        return app, socketio

    def test_session_released_when_handler_raises(self):
        """A handler that opens a session and then raises must still have its
        session cleared, via teardown."""
        app, socketio = self._build_app()

        @socketio.on("boom")
        def boom(data):
            # opens a per-request session (lazily, like any model access)
            Organization(name="ws-teardown-org").save()
            raise RuntimeError("handler blew up mid-event")

        client = socketio.test_client(app)

        with patch.object(
            DatabaseSessionManager,
            "clear_session",
            wraps=DatabaseSessionManager.clear_session,
        ) as clear_spy:
            try:
                client.emit("boom", {})
            except RuntimeError:
                pass  # the test client re-raises the handler's exception

        self.assertTrue(
            clear_spy.called,
            "teardown_request must clear the session even when the handler raises",
        )

    def test_clear_session_noop_without_session(self):
        """teardown fires for every request-context pop, including events that
        never touch the database - clearing must be a no-op, not an error."""
        app, _ = self._build_app()
        with app.test_request_context():
            # no session was ever opened on `g`
            DatabaseSessionManager.clear_session()  # must not raise


class TestWebsocketSessionCleanupWiring(TestResourceBase):
    """The tests above run against a hand-built Flask app, so they would still
    pass if the HQ app stopped registering the hook. This one checks the real
    app."""

    def test_hq_app_registers_teardown_hook(self):
        """Popping a request context of the real HQ app must clear the database
        session. `after_request` does not run for a bare request context (nor
        for socket events), so this only passes if a teardown hook is
        registered."""
        with patch.object(
            DatabaseSessionManager,
            "clear_session",
            wraps=DatabaseSessionManager.clear_session,
        ) as clear_spy:
            with self.server.app.test_request_context():
                DatabaseSessionManager.new_session()

        self.assertTrue(
            clear_spy.called,
            "the HQ app must register a teardown_request hook that clears the "
            "database session",
        )
