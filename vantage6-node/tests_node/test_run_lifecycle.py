import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from kubernetes.client.rest import ApiException

from vantage6.common.enum import AlgorithmStepType, RunStatus

from tests_node.test_container_manager import _get_null_logger, _k8s_runtime, _manager
from vantage6.node import Node
from vantage6.node.container.data_classes import ToBeKilled
from vantage6.node.container.exceptions import PermanentAlgorithmStartFail
from vantage6.node.enum import KillInitiator
from vantage6.node.runtime.base import RunInfo, RunMetadata, RunState

CM = "vantage6.node.container.container_manager"
K8S = "vantage6.node.runtime.kubernetes.runtime"


def _run_info(run_id: int, state: RunState = RunState.SUCCEEDED) -> RunInfo:
    return RunInfo(
        name=f"vantage6-run-{run_id}",
        state=state,
        metadata=RunMetadata(
            run_id=run_id,
            task_id=100 + run_id,
            task_parent_id=None,
            init_org_id=1,
            action=AlgorithmStepType.FEDERATED_COMPUTE,
            session_id=1,
        ),
    )


class TestProcessNextCompletedRun(unittest.TestCase):
    def test_two_finished_runs_are_returned_one_per_call(self):
        runtime = MagicMock()
        remaining = [_run_info(1), _run_info(2)]
        runtime.list_runs.side_effect = lambda: list(remaining)
        runtime.logs.return_value = "logs"
        runtime.remove_run.side_effect = lambda name, run_id: remaining.remove(
            next(r for r in remaining if r.name == name)
        )
        manager = _manager(runtime)

        with patch(f"{CM}.RunIO") as run_io_cls:
            run_io_cls.from_dict.return_value.process_output.return_value = (
                b"out",
                RunStatus.COMPLETED,
            )
            first = manager.process_next_completed_run()
            second = manager.process_next_completed_run()

        self.assertEqual({first.run_id, second.run_id}, {1, 2})
        self.assertEqual(remaining, [])

    def test_failed_run_reports_crash_and_reason(self):
        runtime = MagicMock()
        runtime.list_runs.return_value = [
            RunInfo(
                name="vantage6-run-1",
                state=RunState.FAILED,
                metadata=_run_info(1).metadata,
                exit_code=137,
                reason="OOMKilled",
            )
        ]
        runtime.logs.return_value = "logs"
        manager = _manager(runtime)

        with patch(f"{CM}.RunIO"):
            result = manager.process_next_completed_run()

        self.assertEqual(result.status, RunStatus.CRASHED)
        self.assertIn("OOMKilled", result.logs)
        runtime.remove_run.assert_called_once_with("vantage6-run-1", 1)

    def test_active_runs_are_counted(self):
        runtime = MagicMock()
        runtime.list_runs.return_value = [
            _run_info(1, RunState.RUNNING),
            _run_info(2, RunState.PENDING),
            _run_info(3, RunState.SUCCEEDED),
        ]
        self.assertEqual(_manager(runtime).num_active_tasks, 2)


class TestRunStart(unittest.TestCase):
    def _run(self, runtime) -> RunStatus:
        manager = _manager(runtime)
        task_info = {"id": 5, "init_org": {"id": 1}, "method": "sum", "parent": None}
        with (
            patch(f"{CM}.RunIO") as run_io_cls,
            patch.object(manager, "is_image_allowed", return_value=True),
            patch.object(manager, "_create_mounts", return_value=([], {}, {})),
            patch.object(manager, "_stream_logs") as stream_logs,
        ):
            run_io_cls.return_value.container_name = "vantage6-run-7"
            run_io_cls.return_value.run_id = 7
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
        return status

    def test_exception_while_starting_cleans_up(self):
        runtime = MagicMock()
        runtime.run_exists.return_value = False
        runtime.start_run.side_effect = ApiException(status=500)

        self.assertEqual(self._run(runtime), RunStatus.START_FAILED)
        runtime.remove_run.assert_called_once_with("vantage6-run-7", 7)
        self.stream_logs.assert_not_called()

    def test_active_run_is_streamed(self):
        runtime = MagicMock()
        runtime.run_exists.return_value = False
        runtime.start_run.return_value = RunStatus.ACTIVE

        self.assertEqual(self._run(runtime), RunStatus.ACTIVE)
        runtime.remove_run.assert_not_called()
        self.stream_logs.assert_called_once()

    def test_already_running(self):
        runtime = MagicMock()
        runtime.run_exists.return_value = True

        self.assertEqual(self._run(runtime), RunStatus.ACTIVE)
        runtime.start_run.assert_not_called()


class TestKubernetesStartRun(unittest.TestCase):
    def _start(self, wait_status: RunStatus) -> MagicMock:
        runtime = _k8s_runtime()
        spec = MagicMock()
        spec.name = "vantage6-run-7"
        spec.metadata.run_id = 7
        spec.registries = []
        with (
            patch.object(runtime, "build_job"),
            patch.object(runtime, "_wait_until_pod_running", return_value=wait_status),
            patch(f"{K8S}.delete_run_related_pods") as delete,
        ):
            status = runtime.start_run(spec, Mock())
        self.assertEqual(status, wait_status)
        return delete

    def test_stuck_pod_is_removed(self):
        self._start(RunStatus.NO_DOCKER_IMAGE).assert_called_once()

    def test_running_and_failed_pods_are_kept(self):
        for status in (RunStatus.ACTIVE, RunStatus.FAILED, RunStatus.COMPLETED):
            with self.subTest(status):
                self._start(status).assert_not_called()

    def test_existing_secret_is_replaced(self):
        runtime = _k8s_runtime()
        runtime.core_api.create_namespaced_secret.side_effect = ApiException(status=409)
        secret = MagicMock()
        secret.metadata.name = "vantage6-run-7"
        runtime._create_or_replace_secret(secret)
        runtime.core_api.replace_namespaced_secret.assert_called_once_with(
            name="vantage6-run-7", namespace="tenant", body=secret
        )

    def test_other_secret_errors_are_raised(self):
        runtime = _k8s_runtime()
        runtime.core_api.create_namespaced_secret.side_effect = ApiException(status=403)
        with self.assertRaises(ApiException):
            runtime._create_or_replace_secret(MagicMock())

    def test_list_runs_maps_job_status(self):
        runtime = _k8s_runtime()
        annotations = _run_info(1).metadata.to_dict()

        def job(succeeded, failed):
            return SimpleNamespace(
                metadata=SimpleNamespace(name="j", annotations=annotations),
                status=SimpleNamespace(succeeded=succeeded, failed=failed),
            )

        runtime.batch_api.list_namespaced_job.return_value = SimpleNamespace(
            items=[job(1, None), job(None, 1), job(None, None)]
        )
        self.assertEqual(
            [r.state for r in runtime.list_runs()],
            [RunState.SUCCEEDED, RunState.FAILED, RunState.RUNNING],
        )


class TestValidateSourceDatabase(unittest.TestCase):
    def test_empty_database_list_fails_permanently(self):
        with self.assertRaises(PermanentAlgorithmStartFail):
            _manager()._validate_source_database([])


class TestKill(unittest.TestCase):
    def test_cleanup_reports_node_shutdown(self):
        manager = _manager(MagicMock())
        with patch.object(manager, "_kill_algorithm_runs") as kill:
            manager.cleanup()
        kill.assert_called_once_with(initiator=KillInitiator.NODE_SHUTDOWN)
        manager.runtime.cleanup.assert_called_once()

    def test_kill_list_for_other_organization_kills_nothing(self):
        runtime = MagicMock()
        runtime.list_runs.return_value = [_run_info(1, RunState.RUNNING)]
        manager = _manager(runtime)
        manager.client.whoami.organization_id = 1

        killed = manager.kill_algorithm_runs(
            [ToBeKilled(task_id=101, run_id=1, organization_id=2)]
        )

        self.assertEqual(killed, [])
        runtime.remove_run.assert_not_called()

    def test_kill_list_kills_only_listed_runs(self):
        runtime = MagicMock()
        runtime.list_runs.return_value = [
            _run_info(1, RunState.RUNNING),
            _run_info(2, RunState.RUNNING),
        ]
        runtime.logs.return_value = ""
        manager = _manager(runtime)
        manager.client.whoami.organization_id = 1

        killed = manager.kill_algorithm_runs(
            [ToBeKilled(task_id=102, run_id=2, organization_id=1)]
        )

        self.assertEqual([k.run_id for k in killed], [2])
        runtime.remove_run.assert_called_once_with("vantage6-run-2", 2)

    def test_no_kill_list_kills_all(self):
        runtime = MagicMock()
        runtime.list_runs.return_value = [_run_info(1), _run_info(2)]
        runtime.logs.return_value = ""

        killed = _manager(runtime).kill_algorithm_runs(None)

        self.assertEqual(len(killed), 2)


class TestDuplicateRunCheck(unittest.TestCase):
    def test_running_check_uses_the_container_name(self):
        node = Node.__new__(Node)
        node.log = _get_null_logger()
        node.runs_queue = MagicMock()
        node.container_manager = MagicMock()
        node.container_manager.is_running.return_value = True

        node._Node__add_task_runs_to_queue([{"id": 42, "task": {"id": 1, "name": "t"}}])

        node.container_manager.is_running.assert_called_once_with("vantage6-run-42")
        node.runs_queue.put.assert_not_called()


if __name__ == "__main__":
    unittest.main()
