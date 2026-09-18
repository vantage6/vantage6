import logging
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.node.k8s import container_manager
from vantage6.node.k8s.container_manager import ContainerManager


def get_null_logger(name="null_logger"):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class TestRequireAlgorithmPull(unittest.TestCase):
    """Regression tests for https://github.com/vantage6/vantage6/issues/2732

    The node Helm chart and the documented node configuration place
    ``require_algorithm_pull`` under ``policies``, but the Kubernetes container
    manager read it from ``node``. The documented setting therefore had no
    effect: the job was always created with ``imagePullPolicy: Always`` and
    locally built algorithm images could never run.
    """

    def _make_manager(self, config: dict) -> ContainerManager:
        # Bypass __init__ (it requires a live Kubernetes cluster) and set the
        # attributes that ``run`` touches.
        manager = ContainerManager.__new__(ContainerManager)
        manager.log = get_null_logger()
        manager.ctx = SimpleNamespace(config=config)
        manager.client = MagicMock()
        manager.core_api = MagicMock()
        manager.batch_api = MagicMock()
        manager.task_namespace = "vantage6-tasks"
        manager.task_job_labels = {"node_id": "test-node"}
        manager.num_active_tasks = 0
        return manager

    def _run_and_get_image_pull_policy(self, config: dict) -> str:
        manager = self._make_manager(config)
        run_io = MagicMock()
        run_io.container_name = "run-1"
        run_io.run_id = 1
        task_info = {
            "id": 10,
            "method": "central",
            "parent": None,
            "init_org": {"id": 1},
        }
        with (
            patch.object(container_manager, "RunIO", return_value=run_io),
            patch.object(manager, "is_image_allowed", return_value=True),
            patch.object(manager, "is_running", return_value=False),
            patch.object(
                manager, "_create_volume_mounts", return_value=([], [], {}, {})
            ),
            patch.object(manager, "_validate_environment_variables"),
            patch.object(
                manager,
                "_ContainerManager__wait_until_pod_running",
                return_value=RunStatus.COMPLETED,
            ),
            patch.object(manager, "_stream_logs"),
        ):
            manager.run(
                run_id=1,
                task_info=task_info,
                image="myalg:0.1",
                function_arguments=b"",
                session_id=2,
                token="token",
                databases_to_use=[],
                action=AlgorithmStepType.FEDERATED_COMPUTE,
            )
        _, kwargs = manager.batch_api.create_namespaced_job.call_args
        job = kwargs["body"]
        return job.spec.template.spec.containers[0].image_pull_policy

    def test_policies_require_algorithm_pull_false(self):
        pull_policy = self._run_and_get_image_pull_policy(
            {"policies": {"require_algorithm_pull": False}}
        )
        self.assertEqual(pull_policy, "IfNotPresent")

    def test_policies_require_algorithm_pull_true(self):
        pull_policy = self._run_and_get_image_pull_policy(
            {"policies": {"require_algorithm_pull": True}}
        )
        self.assertEqual(pull_policy, "Always")

    def test_policies_require_algorithm_pull_defaults_to_true(self):
        pull_policy = self._run_and_get_image_pull_policy({"policies": {}})
        self.assertEqual(pull_policy, "Always")


if __name__ == "__main__":
    unittest.main()
