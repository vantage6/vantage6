"""
Behaviour that the container manager relies on, checked against every runtime.
"""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from vantage6.common.enum import AlgorithmStepType, RunStatus

from tests_node.fake_docker import FakeDockerClient
from tests_node.test_container_manager import _k8s_runtime
from tests_node.test_docker_runtime import make_runtime, make_spec
from vantage6.node.runtime.base import ContainerRuntime, RunState
from vantage6.node.runtime.kubernetes.runtime import KubernetesRuntime


class RuntimeContract:
    def make_runtime(self) -> ContainerRuntime:
        raise NotImplementedError

    def restart(self, runtime: ContainerRuntime) -> ContainerRuntime:
        """A new runtime instance over the same platform state."""
        raise NotImplementedError

    def finish(self, runtime: ContainerRuntime, name: str, ok: bool) -> None:
        raise NotImplementedError

    def test_started_run_is_listed_until_removed(self):
        runtime = self.make_runtime()
        spec = make_spec(run_id=7)
        self.assertEqual(runtime.start_run(spec, Mock()), RunStatus.ACTIVE)

        self.assertTrue(runtime.run_exists(spec.name))
        [run] = runtime.list_runs()
        self.assertEqual(run.name, spec.name)
        self.assertFalse(run.state.is_finished)
        self.assertEqual(run.metadata, spec.metadata)

        runtime.remove_run(spec.name, 7)
        self.assertFalse(runtime.run_exists(spec.name))
        self.assertEqual(runtime.list_runs(), [])

    def test_finished_runs(self):
        runtime = self.make_runtime()
        runtime.start_run(make_spec(run_id=1), Mock())
        runtime.start_run(make_spec(run_id=2), Mock())
        self.finish(runtime, "vantage6-run-1", ok=True)
        self.finish(runtime, "vantage6-run-2", ok=False)

        states = {r.metadata.run_id: r.state for r in runtime.list_runs()}
        self.assertEqual(states, {1: RunState.SUCCEEDED, 2: RunState.FAILED})

    def test_runs_survive_a_node_restart(self):
        runtime = self.make_runtime()
        spec = make_spec(run_id=3, step=AlgorithmStepType.DATA_EXTRACTION)
        runtime.start_run(spec, Mock())

        restarted = self.restart(runtime)
        self.assertTrue(restarted.run_exists(spec.name))
        self.assertEqual([r.metadata for r in restarted.list_runs()], [spec.metadata])


class TestDockerContract(RuntimeContract, unittest.TestCase):
    def make_runtime(self):
        return make_runtime(FakeDockerClient())

    def restart(self, runtime):
        return make_runtime(runtime.client)

    def finish(self, runtime, name, ok):
        runtime.client.containers.get(f"{name}-abcdef01").finish(0 if ok else 1)


class FakeKubernetes:
    """Jobs and their pods, as far as the Kubernetes runtime looks at them."""

    def __init__(self):
        self.jobs = {}

    def create_job(self, namespace, body):
        self.jobs[body.metadata.name] = SimpleNamespace(
            metadata=body.metadata,
            status=SimpleNamespace(succeeded=None, failed=None),
        )

    def list_jobs(self, namespace, label_selector):
        return SimpleNamespace(items=list(self.jobs.values()))

    def list_pods(self, namespace, label_selector, **_kwargs):
        name = label_selector.split("=", 1)[1]
        return SimpleNamespace(items=[name] if name in self.jobs else [])

    def delete(self, run_id, container_name, **_kwargs):
        self.jobs.pop(container_name, None)


class TestKubernetesContract(RuntimeContract, unittest.TestCase):
    def setUp(self):
        self.cluster = FakeKubernetes()
        for target, attribute in (
            (KubernetesRuntime, "_wait_until_pod_running"),
            ("vantage6.node.runtime.kubernetes.runtime", "delete_run_related_pods"),
        ):
            if isinstance(target, str):
                patcher = patch(
                    f"{target}.{attribute}", side_effect=self.cluster.delete
                )
            else:
                patcher = patch.object(target, attribute, return_value=RunStatus.ACTIVE)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_runtime(self):
        runtime = _k8s_runtime()
        runtime.batch_api.create_namespaced_job.side_effect = self.cluster.create_job
        runtime.batch_api.list_namespaced_job.side_effect = self.cluster.list_jobs
        runtime.core_api.list_namespaced_pod.side_effect = self.cluster.list_pods
        return runtime

    def restart(self, runtime):
        return self.make_runtime()

    def finish(self, runtime, name, ok):
        status = self.cluster.jobs[name].status
        status.succeeded, status.failed = (1, None) if ok else (None, 1)


if __name__ == "__main__":
    unittest.main()
