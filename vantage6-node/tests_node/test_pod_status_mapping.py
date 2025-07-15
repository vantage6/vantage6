import logging
import unittest

from kubernetes.client import (
    V1Pod,
    V1PodStatus,
    V1ContainerStatus,
    V1PodCondition,
    V1ContainerState,
    V1ContainerStateRunning,
    V1ContainerStateWaiting,
    V1ContainerStateTerminated,
)
from vantage6.node.k8s.jobpod_state_to_run_status_mapper import (
    compute_job_pod_run_status,
)
from vantage6.common.enum import RunStatus


def get_null_logger(name="null_logger"):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class TestPodStatus(unittest.TestCase):

    def setUp(self):

        self.silent_logger = get_null_logger()

        self.running_container_state = V1ContainerState(
            running=V1ContainerStateRunning(started_at="")
        )

        self.waiting_container_state = V1ContainerState(
            waiting=V1ContainerStateWaiting(reason="", message="")
        )

        self.terminated_container_state = V1ContainerState(
            terminated=V1ContainerStateTerminated(exit_code=0, reason="")
        )

        self.mock_container_status = V1ContainerStatus(
            name="",
            ready=True,
            restart_count=1,
            image="",
            image_id="",
            container_id="",
            state=None,  # use running/waiting/terminated_container_state here
            last_state=None,
        )

        self.mock_condition = V1PodCondition(type="", status="", reason="", message="")

        self.mock_pod_status = V1PodStatus(
            phase="",
            reason="",
            conditions=[self.mock_condition],
            container_statuses=[self.mock_container_status],
        )

        self.mock_pod = V1Pod(metadata={"name": ""}, status=self.mock_pod_status)
        pass

    def test_running_job_pod(self):
        self.mock_pod.status.phase = "Running"
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.ACTIVE,
        )

    def test_container_status_not_yet_defined(self):
        self.mock_pod.status.phase = "Pending"
        self.mock_pod.status.container_statuses = None
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.INITIALIZING,
        )

    def test_container_related_err(self):
        self.mock_pod.status.phase = "Pending"
        self.mock_pod.status.container_statuses[0].state = self.waiting_container_state
        self.mock_pod.status.container_statuses[0].state.waiting.reason = (
            "ImagePullBackOff"
        )
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.NO_DOCKER_IMAGE,
        )

    def test_waiting_reason_not_ready_err(self):
        self.mock_pod.status.phase = "Pending"
        self.mock_pod.status.container_statuses[0].state = self.waiting_container_state
        self.mock_pod.status.container_statuses[0].state.waiting = None
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.INITIALIZING,
        )

    def test_container_runtime_error(self):
        self.mock_pod.status.phase = "Pending"
        self.mock_pod.status.container_statuses[0].state = self.waiting_container_state
        self.mock_pod.status.container_statuses[0].state.waiting.reason = (
            "CrashLoopBackOff"
        )
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.CRASHED,
        )

    def test_completed_job(self):
        self.mock_pod.status.phase = "Succeded"
        self.assertEqual(
            compute_job_pod_run_status(
                log=self.silent_logger, task_namespace="", label="", pod=self.mock_pod
            ),
            RunStatus.COMPLETED,
        )
