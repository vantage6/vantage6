import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from kubernetes.client.rest import ApiException

from vantage6.common.enum import AlgorithmStepType, RunStatus

from tests_node.test_container_manager import _get_null_logger, _manager
from vantage6.node import Node
from vantage6.node.enum import KillInitiator
from vantage6.node.k8s.container_manager import ContainerManager
from vantage6.node.k8s.data_classes import ToBeKilled
from vantage6.node.k8s.exceptions import PermanentAlgorithmStartFail

CM = "vantage6.node.k8s.container_manager"


def _job(run_id: int, succeeded: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(
            annotations={
                "run_id": str(run_id),
                "task_id": str(100 + run_id),
                "task_parent_id": "",
                "init_org_id": "1",
                "action": AlgorithmStepType.FEDERATED_COMPUTE.value,
                "session_id": "1",
                "df_name": "",
                "df_id": "",
                "df_label": "",
            }
        ),
        status=SimpleNamespace(succeeded=1 if succeeded else None, failed=None),
    )


def _lifecycle_manager() -> ContainerManager:
    manager = _manager()
    manager.ctx = MagicMock()
    manager.ctx.config = {}
    manager.client = MagicMock()
    manager.core_api = MagicMock()
    manager.batch_api = MagicMock()
    manager.task_job_label_selector = "node_id=abc"
    manager.num_active_tasks = 0
    return manager


class TestProcessNextCompletedRun(unittest.TestCase):
    def test_two_finished_jobs_are_returned_one_per_call(self):
        manager = _lifecycle_manager()
        manager.num_active_tasks = 2
        remaining = [_job(1), _job(2)]

        def list_jobs(*_args, **_kwargs):
            return SimpleNamespace(items=list(remaining))

        def delete(run_id, **_kwargs):
            remaining[:] = [
                j for j in remaining if j.metadata.annotations["run_id"] != str(run_id)
            ]

        def from_dict(annotations, *_args, **_kwargs):
            run_io = MagicMock()
            run_io.run_id = int(annotations["run_id"])
            run_io.process_output.return_value = (b"out", RunStatus.COMPLETED)
            return run_io

        manager.batch_api.list_namespaced_job.side_effect = list_jobs
        with (
            patch(f"{CM}.RunIO") as run_io_cls,
            patch(f"{CM}.delete_run_related_pods", side_effect=delete),
            patch.object(manager, "_get_logs", return_value="logs"),
        ):
            run_io_cls.from_dict.side_effect = from_dict
            first = manager.process_next_completed_run()
            second = manager.process_next_completed_run()

        self.assertEqual({first.run_id, second.run_id}, {1, 2})
        self.assertEqual(manager.num_active_tasks, 0)

    def test_counter_never_goes_negative(self):
        manager = _lifecycle_manager()
        manager._decrement_active_tasks()
        self.assertEqual(manager.num_active_tasks, 0)


class TestRunStartFailures(unittest.TestCase):
    def _run(self, manager: ContainerManager, **patches) -> RunStatus:
        task_info = {"id": 5, "init_org": {"id": 1}, "method": "sum", "parent": None}
        with (
            patch(f"{CM}.RunIO"),
            patch.object(manager, "is_image_allowed", return_value=True),
            patch.object(manager, "is_running", return_value=False),
            patch.object(
                manager, "_create_volume_mounts", return_value=([], [], {}, {})
            ),
            patch.object(manager, "_stream_logs") as stream_logs,
            patch(f"{CM}.delete_run_related_pods") as delete,
            patch.object(manager, "_create_and_start_job", **patches),
        ):
            status = manager.run(
                run_id=7,
                task_info=task_info,
                image="img",
                function_arguments=b"",
                session_id=1,
                token="",
                databases_to_use=[],
                action=AlgorithmStepType.FEDERATED_COMPUTE,
                on_status_change=Mock(),
            )
        self.stream_logs = stream_logs
        self.delete = delete
        return status

    def test_exception_while_creating_job_cleans_up(self):
        manager = _lifecycle_manager()
        status = self._run(manager, side_effect=ApiException(status=500))
        self.assertEqual(status, RunStatus.START_FAILED)
        self.delete.assert_called_once()
        self.assertEqual(manager.num_active_tasks, 0)

    def test_stuck_pod_cleans_up_and_is_not_counted(self):
        manager = _lifecycle_manager()
        status = self._run(manager, return_value=RunStatus.NO_DOCKER_IMAGE)
        self.assertEqual(status, RunStatus.NO_DOCKER_IMAGE)
        self.delete.assert_called_once()
        self.stream_logs.assert_not_called()
        self.assertEqual(manager.num_active_tasks, 0)

    def test_active_run_is_counted_and_streamed(self):
        manager = _lifecycle_manager()
        status = self._run(manager, return_value=RunStatus.ACTIVE)
        self.assertEqual(status, RunStatus.ACTIVE)
        self.delete.assert_not_called()
        self.stream_logs.assert_called_once()
        self.assertEqual(manager.num_active_tasks, 1)

    def test_failed_pod_is_left_for_the_completion_loop(self):
        manager = _lifecycle_manager()
        status = self._run(manager, return_value=RunStatus.FAILED)
        self.assertEqual(status, RunStatus.FAILED)
        self.delete.assert_not_called()
        self.stream_logs.assert_not_called()
        self.assertEqual(manager.num_active_tasks, 1)


class TestSecretReplacement(unittest.TestCase):
    def test_existing_secret_is_replaced(self):
        manager = _lifecycle_manager()
        manager.core_api.create_namespaced_secret.side_effect = ApiException(status=409)
        secret = MagicMock()
        secret.metadata.name = "vantage6-run-7"
        manager._create_or_replace_secret(secret)
        manager.core_api.replace_namespaced_secret.assert_called_once_with(
            name="vantage6-run-7", namespace="tenant", body=secret
        )

    def test_other_errors_are_raised(self):
        manager = _lifecycle_manager()
        manager.core_api.create_namespaced_secret.side_effect = ApiException(status=403)
        with self.assertRaises(ApiException):
            manager._create_or_replace_secret(MagicMock())


class TestValidateSourceDatabase(unittest.TestCase):
    def test_empty_database_list_fails_permanently(self):
        manager = _manager()
        manager.databases = {}
        with self.assertRaises(PermanentAlgorithmStartFail):
            manager._validate_source_database([])


class TestKill(unittest.TestCase):
    def test_cleanup_reports_node_shutdown(self):
        manager = _manager()
        with patch.object(manager, "_kill_algorithm_runs") as kill:
            manager.cleanup()
        kill.assert_called_once_with(initiator=KillInitiator.NODE_SHUTDOWN)

    def test_kill_list_for_other_organization_kills_nothing(self):
        manager = _lifecycle_manager()
        manager.client.whoami.organization_id = 1
        manager.batch_api.list_namespaced_job.return_value = SimpleNamespace(
            items=[_job(1)]
        )
        with patch(f"{CM}.delete_run_related_pods") as delete:
            killed = manager.kill_algorithm_runs(
                [ToBeKilled(task_id=101, run_id=1, organization_id=2)]
            )
        self.assertEqual(killed, [])
        delete.assert_not_called()


class TestDuplicateRunCheck(unittest.TestCase):
    def test_running_check_uses_the_job_label(self):
        node = Node.__new__(Node)
        node.log = _get_null_logger()
        node.runs_queue = MagicMock()
        node.k8s_container_manager = MagicMock()
        node.k8s_container_manager.is_running.return_value = True

        node._Node__add_task_runs_to_queue([{"id": 42, "task": {"id": 1, "name": "t"}}])

        node.k8s_container_manager.is_running.assert_called_once_with("vantage6-run-42")
        node.runs_queue.put.assert_not_called()


if __name__ == "__main__":
    unittest.main()
