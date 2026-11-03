from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid1

from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.hq.model import (
    Collaboration,
    Organization,
    Run,
    Session,
    Task,
)
from vantage6.hq.model.dataframe_to_be_deleted_at_node import (
    DataframeToBeDeletedAtNode,
)
from vantage6.hq.websockets import DefaultSocketNamespace

from .test_resource_base import TestResourceBase


class TestSocketEventVerification(TestResourceBase):
    def setUp(self):
        super().setUp()
        self.namespace = DefaultSocketNamespace(
            "/tasks", socketio=MagicMock(), metrics=MagicMock()
        )

        self.org_a = Organization()
        self.org_b = Organization()
        self.col = Collaboration(organizations=[self.org_a, self.org_b])
        self.col_other = Collaboration(organizations=[self.org_a])
        self.node_a = self.create_node(organization=self.org_a, collaboration=self.col)
        self.node_b = self.create_node(organization=self.org_b, collaboration=self.col)
        self.node_a_other_col = self.create_node(
            organization=self.org_a, collaboration=self.col_other
        )

        self.parent_task = Task(collaboration=self.col, init_org=self.org_a)
        self.parent_task.save()
        self.task = Task(
            collaboration=self.col,
            init_org=self.org_a,
            parent=self.parent_task,
            job_id=4242,
        )
        self.task.save()
        self.run_a = Run(
            task=self.task,
            organization=self.org_a,
            status=RunStatus.ACTIVE.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        )
        self.run_a.save()
        self.run_b = Run(
            task=self.task,
            organization=self.org_b,
            status=RunStatus.ACTIVE.value,
            action=AlgorithmStepType.CENTRAL_COMPUTE.value,
        )
        self.run_b.save()

    def _call(self, handler: str, data: dict, node=None, client_type="node"):
        auth_id = node.keycloak_id if node else "some-user"
        socket_session = SimpleNamespace(type=client_type, auth_id=auth_id)
        with (
            patch("vantage6.hq.websockets.session", socket_session),
            patch("vantage6.hq.websockets.emit") as mock_emit,
        ):
            getattr(self.namespace, handler)(data)
        return mock_emit

    def _status_emits(self, mock_emit):
        return [
            c
            for c in mock_emit.call_args_list
            if c.args[0] == "algorithm_status_change"
        ]

    def test_status_change_own_run_uses_derived_values(self):
        forged = {
            "run_id": self.run_a.id,
            "status": RunStatus.COMPLETED.value,
            "task_id": 9999,
            "collaboration_id": 9999,
            "node_id": 9999,
            "organization_id": 9999,
            "parent_id": 9999,
        }
        mock_emit = self._call("on_algorithm_status_change", forged, self.node_a)

        emits = self._status_emits(mock_emit)
        self.assertEqual(len(emits), 1)
        payload = emits[0].args[1]
        self.assertEqual(payload["run_id"], self.run_a.id)
        self.assertEqual(payload["status"], RunStatus.COMPLETED.value)
        self.assertEqual(payload["task_id"], self.task.id)
        self.assertEqual(payload["job_id"], 4242)
        self.assertEqual(payload["collaboration_id"], self.col.id)
        self.assertEqual(payload["node_id"], self.node_a.id)
        self.assertEqual(payload["organization_id"], self.org_a.id)
        self.assertEqual(payload["parent_id"], self.parent_task.id)
        self.assertEqual(emits[0].kwargs["room"], f"collaboration_{self.col.id}")

    def test_status_change_other_org_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_b.id, "status": RunStatus.COMPLETED.value},
            self.node_a,
        )
        mock_emit.assert_not_called()

    def test_status_change_from_other_collaboration_is_ignored(self):
        # same organization, but its node in a different collaboration
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_a.id, "status": RunStatus.COMPLETED.value},
            self.node_a_other_col,
        )
        mock_emit.assert_not_called()

    def test_status_change_unknown_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": 999999, "status": RunStatus.COMPLETED.value},
            self.node_a,
        )
        mock_emit.assert_not_called()

    def test_status_change_malformed_run_id_is_ignored(self):
        run_id = self.run_a.id
        for malformed_id in ([run_id], {"id": run_id}, str(run_id)):
            mock_emit = self._call(
                "on_algorithm_status_change",
                {"run_id": malformed_id, "status": RunStatus.COMPLETED.value},
                self.node_a,
            )
            mock_emit.assert_not_called()

    def test_status_change_invalid_status_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_status_change",
            {"run_id": self.run_a.id, "status": "totally-made-up"},
            self.node_a,
        )
        mock_emit.assert_not_called()

    def test_algorithm_log_own_run(self):
        mock_emit = self._call(
            "on_algorithm_log",
            {"run_id": self.run_a.id, "collaboration_id": 9999, "log": "hello"},
            self.node_a,
        )
        self.assertIn("hello", Run.get(self.run_a.id).log)
        mock_emit.assert_called_once()
        self.assertEqual(
            mock_emit.call_args.args[1],
            {"run_id": self.run_a.id, "task_id": self.task.id, "log": "hello"},
        )
        self.assertEqual(
            mock_emit.call_args.kwargs["room"], f"collaboration_{self.col.id}"
        )

    def test_algorithm_log_other_org_run_is_ignored(self):
        mock_emit = self._call(
            "on_algorithm_log",
            {"run_id": self.run_b.id, "log": "injected"},
            self.node_a,
        )
        self.assertFalse(Run.get(self.run_b.id).log)
        mock_emit.assert_not_called()

    def _create_deletion_records(self):
        df_name = str(uuid1())
        user = self.create_user()
        df_session = Session(name=str(uuid1()), user_id=user.id, collaboration=self.col)
        df_session.save()
        record_a = DataframeToBeDeletedAtNode(
            dataframe_name=df_name, session_id=df_session.id, node_id=self.node_a.id
        )
        record_a.save()
        record_b = DataframeToBeDeletedAtNode(
            dataframe_name=df_name, session_id=df_session.id, node_id=self.node_b.id
        )
        record_b.save()
        return df_name, df_session, record_a, record_b

    def test_dataframe_deleted_as_user_is_ignored(self):
        df_name, df_session, record_a, _ = self._create_deletion_records()
        self._call(
            "on_dataframe_deleted",
            {
                "df_name": df_name,
                "session_id": df_session.id,
                "node_id": self.node_a.id,
            },
            client_type="user",
        )
        self.assertIsNotNone(DataframeToBeDeletedAtNode.get(record_a.id))

    def test_dataframe_deleted_ignores_forged_node_id(self):
        df_name, df_session, record_a, record_b = self._create_deletion_records()
        # node A claims to be node B
        self._call(
            "on_dataframe_deleted",
            {
                "df_name": df_name,
                "session_id": df_session.id,
                "node_id": self.node_b.id,
            },
            self.node_a,
        )
        self.assertIsNotNone(DataframeToBeDeletedAtNode.get(record_b.id))
        self.assertIsNone(DataframeToBeDeletedAtNode.get(record_a.id))

    def test_dataframe_deleted_without_record_is_ignored(self):
        # no deletion instruction exists for this node: must not raise
        self._call(
            "on_dataframe_deleted",
            {"df_name": "does-not-exist", "session_id": 999999},
            self.node_a,
        )
