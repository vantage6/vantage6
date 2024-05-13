from vantage6.common.enums import SessionStatus
from vantage6.server.model.session import Session
from vantage6.server.model.node_session import NodeSession
from vantage6.server.model.node_session_config import NodeSessionConfig


from .test_model_base import TestModelBase


class TestModelNodeSessionConfig(TestModelBase):

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

        # create a node session config
        node_session_config = NodeSessionConfig(
            node_session_id=node_session.id, key="test_key", value="test_value"
        )
        node_session_config.save()
        self.addCleanup(node_session_config.delete)

        self.assertIsInstance(node_session_config, NodeSessionConfig)
        self.assertEqual(node_session_config.node_session_id, node_session.id)
        self.assertEqual(node_session_config.key, "test_key")
        self.assertEqual(node_session_config.value, "test_value")
