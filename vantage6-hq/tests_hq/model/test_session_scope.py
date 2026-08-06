"""
Regression test for issue #2656 (DetachedInstanceError).

The per-request database session is scoped to the Flask *request context*
rather than to the greenlet/thread. This guards against a socket-event handler
that runs synchronously inside a request's ``socketio.emit()`` (e.g. a node
disconnect triggered by delivering to a half-open client): such a handler runs
in a nested request context but the same greenlet, and its ``clear_session()``
must not detach the ORM objects the outer request is still holding.

Without the fix (session scoped per greenlet) the assertion below raises
``DetachedInstanceError``; with it the outer request keeps its own session.
"""

from unittest import TestCase

from flask import Flask

from vantage6.hq.model import Organization
from vantage6.hq.model.base import Database, DatabaseSessionManager


class TestSessionScopePerRequestContext(TestCase):
    @classmethod
    def setUpClass(cls):
        Database().connect("sqlite://", allow_drop_all=True)
        cls.app = Flask(__name__)

    @classmethod
    def tearDownClass(cls):
        Database().clear_data()
        Database().close()

    def test_nested_request_context_clear_does_not_detach_outer_session(self):
        # Outer request context (the HTTP PATCH handler).
        with self.app.test_request_context():
            org = Organization(name="outer-request-org")
            org.save()  # commit expires all attributes (expire_on_commit=True)

            # A socket handler dispatched inside socketio.emit() runs in its own
            # request context (Flask-SocketIO: `with app.request_context(...)`)
            # but the same greenlet. It does unrelated DB work and clears the
            # session in its cleanup.
            with self.app.test_request_context():
                DatabaseSessionManager.new_session()
                unrelated = Organization(name="disconnect-handler-org")
                unrelated.save()
                DatabaseSessionManager.clear_session()

            # Back in the outer request: reading an expired attribute must still
            # work. This is the exact operation that failed at run.py:743.
            self.assertEqual(org.name, "outer-request-org")

            DatabaseSessionManager.clear_session()
