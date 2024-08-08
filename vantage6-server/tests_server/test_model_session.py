import datetime

from sqlalchemy.exc import IntegrityError

from vantage6.common.enum import SessionStatus
from vantage6.server.model import Session
from vantage6.server.model.rule import Scope

from .test_model_base import TestModelBase


class TestModelSession(TestModelBase):

    def test_creation(self):

        # create a session
        session = Session(label="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)

        self.assertIsInstance(session, Session)
        self.assertEqual(session.label, "test_session")
        self.assertEqual(session.user_id, 1)
        self.assertEqual(session.collaboration_id, 1)
        self.assertIsInstance(session.created_at, datetime.datetime)
        self.assertIsInstance(session.last_used_at, datetime.datetime)
        self.assertIsInstance(session.scope, Scope)
        self.assertEqual(session.scope, Scope.OWN)

    def test_unique_constrain(self):

        # each label should be unique within a collaboration
        session = Session(label="test_session", user_id=1, collaboration_id=1)
        session.save()

        session2 = Session(label="test_session", user_id=1, collaboration_id=1)
        self.assertRaises(IntegrityError, session2.save)
        self.addCleanup(session.delete)

    def test_is_ready(self):

        session = Session(label="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)

        # add some dummy node sessions
        # n_ses = NodeSession(node_id=1, session=session, state=SessionStatus.PENDING)
        # n_ses.save()
        # self.addCleanup(n_ses.delete)

        # self.assertFalse(session.is_ready)

        # n_ses.state = SessionStatus.READY
        # n_ses.save()

        # self.assertTrue(session.is_ready)
