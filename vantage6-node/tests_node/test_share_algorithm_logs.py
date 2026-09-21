import unittest
from unittest.mock import Mock, patch

from vantage6.common.enum import RunStatus

from vantage6.node import Node
from vantage6.node.k8s.container_manager import ContainerManager
from vantage6.node.k8s.data_classes import KilledRun, Result


class TestContainerManagerLogSharing(unittest.TestCase):
    def _make_manager(self, share_algorithm_logs: bool) -> ContainerManager:
        manager = ContainerManager.__new__(ContainerManager)
        manager.log = Mock()
        manager.share_algorithm_logs = share_algorithm_logs
        manager.socket_io = Mock()
        manager.client = Mock()
        manager.client.collaboration_id = 7
        manager.task_namespace = "test-namespace"
        manager.core_api = Mock()
        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "pod-1"
        manager.core_api.list_namespaced_pod.return_value.items = [pod]
        return manager

    def test_log_stream_does_not_emit_when_sharing_disabled(self):
        manager = self._make_manager(False)
        run_io = Mock(run_id=42, container_name="algo-container")
        fake_watch = Mock()
        fake_watch.stream.return_value = ["hello from algorithm"]

        with patch(
            "vantage6.node.k8s.container_manager.watch.Watch", return_value=fake_watch
        ):
            manager._ContainerManager__log_stream(run_io=run_io, task_id=99)

        manager.socket_io.emit.assert_not_called()

    def test_log_stream_emits_when_sharing_enabled(self):
        manager = self._make_manager(True)
        run_io = Mock(run_id=42, container_name="algo-container")
        fake_watch = Mock()
        fake_watch.stream.return_value = ["hello from algorithm"]

        with patch(
            "vantage6.node.k8s.container_manager.watch.Watch", return_value=fake_watch
        ):
            manager._ContainerManager__log_stream(run_io=run_io, task_id=99)

        manager.socket_io.emit.assert_called_once_with(
            "algorithm_log",
            {
                "collaboration_id": 7,
                "run_id": 42,
                "task_id": 99,
                "log": "hello from algorithm",
            },
            namespace="/tasks",
        )


class TestFinishedTaskLogSharing(unittest.TestCase):
    def _make_node(self, share_algorithm_logs: bool) -> Node:
        node = Node.__new__(Node)
        node.log = Mock()
        node.config = {"share_algorithm_logs": share_algorithm_logs}
        node.k8s_container_manager = Mock()
        node.k8s_container_manager.process_next_completed_run.return_value = Result(
            run_id=1,
            task_id=2,
            logs="sensitive algorithm logs",
            data="output-data",
            status=RunStatus.COMPLETED,
            parent_id=None,
        )
        node.client = Mock()
        node.client.request.side_effect = [
            {"task": {"id": 2}},
            {"init_org": {"id": 5}},
        ]
        node.client.whoami = Mock(id_=1, organization_id=1)
        node.client.collaboration_id = 1
        node.socketIO = Mock()
        return node

    def _run_one_iteration(self, node: Node) -> None:
        # __send_updates_finished_tasks loops forever with a trailing
        # time.sleep(1); make sleep raise so the loop stops after one pass.
        with (
            patch("vantage6.node.time.sleep", side_effect=InterruptedError),
            self.assertRaises(InterruptedError),
        ):
            node._Node__send_updates_finished_tasks()

    def test_logs_redacted_when_sharing_disabled(self):
        node = self._make_node(share_algorithm_logs=False)
        self._run_one_iteration(node)

        patch_call = node.client.run.patch.call_args
        self.assertEqual(
            patch_call.kwargs["data"]["log"],
            "Node does not allow sharing algorithm logs",
        )

    def test_logs_shared_when_sharing_enabled(self):
        node = self._make_node(share_algorithm_logs=True)
        self._run_one_iteration(node)

        patch_call = node.client.run.patch.call_args
        self.assertEqual(patch_call.kwargs["data"]["log"], "sensitive algorithm logs")


class TestKillContainersLogSharing(unittest.TestCase):
    def _make_node(self, share_algorithm_logs: bool) -> Node:
        node = Node.__new__(Node)
        node.log = Mock()
        node.config = {"share_algorithm_logs": share_algorithm_logs}
        node.client = Mock()
        node.client.collaboration_id = 7
        node.client.whoami = Mock(id_=1)
        node.k8s_container_manager = Mock()
        node.k8s_container_manager.kill_algorithm_runs.return_value = [
            KilledRun(run_id=1, task_id=2, parent_id=None, logs="sensitive kill logs")
        ]
        return node

    def test_kill_logs_not_sent_when_sharing_disabled(self):
        node = self._make_node(share_algorithm_logs=False)
        node.kill_containers({"collaboration_id": 7})

        node.client.run.patch.assert_not_called()

    def test_kill_logs_sent_when_sharing_enabled(self):
        node = self._make_node(share_algorithm_logs=True)
        node.kill_containers({"collaboration_id": 7})

        node.client.run.patch.assert_called_once_with(
            id_=1, data={"log": "sensitive kill logs"}
        )


if __name__ == "__main__":
    unittest.main()
