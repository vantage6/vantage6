import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid1

from vantage6.common.task_status import TaskStatus
from vantage6.server.model import Collaboration, Node, Organization, Run, Task
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.websockets import DefaultSocketNamespace


class TestSocketEventVerification(unittest.TestCase):
    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        DatabaseSessionManager.get_session()

        self.namespace = DefaultSocketNamespace(
            "/tasks", socketio=MagicMock(), metrics=MagicMock()
        )

        self.org_a = Organization(name=str(uuid1()))
        self.org_b = Organization(name=str(uuid1()))
        self.col = Collaboration(
            name=str(uuid1()), organizations=[self.org_a, self.org_b]
        )
        self.col_other = Collaboration(name=str(uuid1()), organizations=[self.org_a])
        self.node_a = self._create_node(self.org_a, self.col)
        self.node_b = self._create_node(self.org_b, self.col)
        self.node_a_other_col = self._create_node(self.org_a, self.col_other)

        parent_task = Task(collaboration=self.col, init_org=self.org_a)
        parent_task.save()
        task = Task(
            collaboration=self.col,
            init_org=self.org_a,
            parent=parent_task,
            job_id=4242,
        )
        task.save()
        run_a = Run(task=task, organization=self.org_a, status=TaskStatus.ACTIVE)
        run_a.save()
        run_b = Run(task=task, organization=self.org_b, status=TaskStatus.ACTIVE)
        run_b.save()

        # store ids: handlers clear the database session, detaching objects
        self.col_id = self.col.id
        self.org_a_id = self.org_a.id
        self.node_a_id = self.node_a.id
        self.parent_task_id = parent_task.id
        self.task_id = task.id
        self.run_a_id = run_a.id
        self.run_b_id = run_b.id

    def tearDown(self):
        Database().clear_data()

    @staticmethod
    def _create_node(organization, collaboration):
        node = Node(
            name=str(uuid1()),
            api_key=str(uuid1()),
            organization=organization,
            collaboration=collaboration,
        )
        node.save()
        return node

    def _call(self, handler: str, data: dict, node_id=None, client_type="node"):
        socket_session = SimpleNamespace(type=client_type, auth_id=node_id)
        with (
            patch("vantage6.server.websockets.session", socket_session),
            patch("vantage6.server.websockets.emit") as mock_emit,
        ):
            getattr(self.namespace, handler)(data)
        return mock_emit

    def test_status_change_own_run_uses_derived_values(self):
        forged = {
            "run_id": self.run_a_id,
            "status": TaskStatus.COMPLETED.value,
            "task_id": 9999,
            "collaboration_id": 9999,
            "node_id": 9999,
            "organization_id": 9999,
            "parent_id": 9999,
        }
        mock_emit = self._call("on_algorithm_status_change", forged, self.node_a_id)

        mock_emit.assert_called_once()
        payload = mock_emit.call_args.args[1]
        self.assertEqual(payload["run_id"], self.run_a_id)
        self.assertEqual(payload["status"], TaskStatus.COMPLETED.value)
        self.assertEqual(payload["task_id"], self.task_id)
        self.assertEqual(payload["job_id"], 4242)
        self.assertEqual(payload["collaboration_id"], self.col_id)
        self.assertEqual(payload["node_id"], self.node_a_id)
        self.assertEqual(payload["organization_id"], self.org_a_id)
        self.assertEqual(payload["parent_id"], self.parent_task_id)
        self.assertEqual(
            mock_emit.call_args.kwargs["room"], f"collaboration_{self.col_id}"
        )

    def test_status_change_other_org_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_b_id, "status": TaskStatus.COMPLETED.value},
            self.node_a_id,
        )
        mock_emit.assert_not_called()

    def test_status_change_from_other_collaboration_is_ignored(self):
        # same organization, but its node in a different collaboration
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_a_id, "status": TaskStatus.COMPLETED.value},
            self.node_a_other_col.id,
        )
        mock_emit.assert_not_called()

    def test_status_change_unknown_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": 999999, "status": TaskStatus.COMPLETED.value},
            self.node_a_id,
        )
        mock_emit.assert_not_called()

    def test_status_change_invalid_status_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_a_id, "status": "totally-made-up"},
            self.node_a_id,
        )
        mock_emit.assert_not_called()

    def test_algorithm_log_own_run(self):
        mock_emit = self._call(
            "on_algorithm_log",
            {"run_id": self.run_a_id, "collaboration_id": 9999, "log": "hello"},
            self.node_a_id,
        )
        self.assertIn("hello", Run.get(self.run_a_id).log)
        mock_emit.assert_called_once()
        self.assertEqual(
            mock_emit.call_args.args[1],
            {"run_id": self.run_a_id, "task_id": self.task_id, "log": "hello"},
        )
        self.assertEqual(
            mock_emit.call_args.kwargs["room"], f"collaboration_{self.col_id}"
        )

    def test_algorithm_log_other_org_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_log",
            {"run_id": self.run_b_id, "log": "injected"},
            self.node_a_id,
        )
        self.assertFalse(Run.get(self.run_b_id).log)
        mock_emit.assert_not_called()
