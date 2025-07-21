import datetime

from sqlalchemy.exc import IntegrityError

from vantage6.server.model import Session
from vantage6.server.model.rule import Scope

from .test_model_base import TestModelBase


class TestModelSession(TestModelBase):

    def test_creation(self):

        # create a session
        session = Session(name="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)

        self.assertIsInstance(session, Session)
        self.assertEqual(session.name, "test_session")
        self.assertEqual(session.user_id, 1)
        self.assertEqual(session.collaboration_id, 1)
        self.assertIsInstance(session.created_at, datetime.datetime)
        self.assertIsInstance(session.last_used_at, datetime.datetime)
        self.assertEqual(session.scope, Scope.OWN.value)

    def test_unique_constraint(self):

        # each label should be unique within a collaboration
        session = Session(name="test_session", user_id=1, collaboration_id=1)
        session.save()

        session2 = Session(name="test_session", user_id=1, collaboration_id=1)
        self.assertRaises(IntegrityError, session2.save)
        self.addCleanup(session.delete)

    def test_is_ready(self):

        session = Session(name="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)
