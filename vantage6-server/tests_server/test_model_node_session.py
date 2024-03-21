import datetime

from sqlalchemy.exc import IntegrityError

from vantage6.server.model.session import Session
from vantage6.server.model.node_session import NodeSession
from vantage6.common.session_status import SessionStatus

from .test_model_base import TestModelBase


class TestModelNodeSession(TestModelBase):

    def test_creation(self):

        # create a session
        session = Session(label="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)

        # create a node session
        node_session = NodeSession(
            node_id=1, session=session, state=SessionStatus.PENDING
        )
        node_session.save()
        self.addCleanup(node_session.delete)

        self.assertIsInstance(node_session, NodeSession)
        self.assertEqual(node_session.node_id, 1)
        self.assertEqual(node_session.session_id, session.id)
        self.assertIsInstance(node_session.state, SessionStatus)
        self.assertEqual(node_session.state, SessionStatus.PENDING)
        self.assertIsInstance(node_session.last_updated_at, datetime.datetime)

    def test_unique_constrain(self):

        # each node can only have one session
        session = Session(label="test_session", user_id=1, collaboration_id=1)
        session.save()
        self.addCleanup(session.delete)

        node_session = NodeSession(
            node_id=1, session=session, state=SessionStatus.PENDING
        )
        node_session.save()
        self.addCleanup(node_session.delete)

        node_session2 = NodeSession(
            node_id=1, session=session, state=SessionStatus.PENDING
        )
        self.assertRaises(IntegrityError, node_session2.save)
