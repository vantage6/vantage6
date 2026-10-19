import unittest
from unittest.mock import Mock, patch

from socketio.exceptions import BadNamespaceError

from vantage6.common.enum import RunStatus

from vantage6.node import Node


class TestEmitAlgorithmStatusChange(unittest.TestCase):
    def setUp(self):
        self.node = Node.__new__(Node)
        self.node.log = Mock()
        self.node.client = Mock()
        self.node.client.whoami.id_ = 1
        self.node.client.whoami.organization_id = 2
        self.node.client.collaboration_id = 3
        self.node.socketIO = Mock()
        self.node.socketIO.namespaces = {"/tasks": "sid"}

    def _emit(self):
        with patch("vantage6.node.time.sleep"):
            self.node._Node__emit_algorithm_status_change(
                task_id=10, run_id=20, parent_id=None, status=RunStatus.ACTIVE
            )

    def test_emit_when_connected(self):
        self._emit()

        self.node.socketIO.emit.assert_called_once_with(
            "algorithm_status_change",
            data={
                "node_id": 1,
                "status": RunStatus.ACTIVE.value,
                "run_id": 20,
                "task_id": 10,
                "collaboration_id": 3,
                "organization_id": 2,
                "parent_id": None,
            },
            namespace="/tasks",
        )
        self.node.log.warning.assert_not_called()

    def test_skip_when_namespace_never_connects(self):
        self.node.socketIO.namespaces = {}

        self._emit()

        self.node.socketIO.emit.assert_not_called()
        self.node.log.warning.assert_called_once()

    def test_no_exception_when_namespace_drops_during_emit(self):
        self.node.socketIO.emit.side_effect = BadNamespaceError("/tasks")

        self._emit()

        self.node.log.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
