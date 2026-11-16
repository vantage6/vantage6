"""
The Docker runtime against a real Docker engine. Pulls and builds small images, so
it only runs with V6_DOCKER_INTEGRATION=1:

    V6_DOCKER_INTEGRATION=1 python -m unittest tests_node.test_docker_daemon
"""

import io
import os
import tempfile
import time
import unittest
import uuid
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.node.runtime.base import (
    MountSpec,
    PullPolicy,
    RunMetadata,
    RunSpec,
    RunState,
    StorageKind,
    StorageRef,
)

ENABLED = os.environ.get("V6_DOCKER_INTEGRATION") == "1"
TASK = StorageRef(StorageKind.TASK)

IMAGES = {
    "v6-it-sleep": 'FROM alpine:3\nCMD ["sleep", "120"]\n',
    "v6-it-oom": 'FROM alpine:3\nCMD ["tail", "/dev/zero"]\n',
    "v6-it-internet": (
        "FROM curlimages/curl:8.11.1\n"
        'ENTRYPOINT ["curl", "-s", "-o", "/dev/null", "--max-time", "5", '
        '"https://example.com"]\n'
    ),
}


@unittest.skipUnless(ENABLED, "set V6_DOCKER_INTEGRATION=1 to run")
class TestDockerDaemon(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import docker

        from vantage6.node.runtime.docker.runtime import DockerRuntime

        cls.client = docker.from_env()
        for tag, dockerfile in IMAGES.items():
            cls.client.images.build(fileobj=io.BytesIO(dockerfile.encode()), tag=tag)

        cls.tmp = tempfile.TemporaryDirectory()
        cls.tasks = Path(cls.tmp.name).resolve()
        suffix = uuid.uuid4().hex[:6]
        cls.node_name = f"v6-it-node-{suffix}"
        cls.egress = f"v6-it-net-{suffix}"
        cls.client.networks.create(cls.egress)
        # Stands in for the node container: the runtime reads its mounts
        cls.node = cls.client.containers.run(
            "v6-it-sleep",
            name=cls.node_name,
            detach=True,
            volumes={str(cls.tasks): {"bind": "/app/tasks", "mode": "rw"}},
            network=cls.egress,
        )

        ctx = MagicMock()
        ctx.identifier = uuid.uuid4().hex[:16]
        ctx.config = {
            "docker": {
                "node_container": cls.node_name,
                "egress_network": cls.egress,
                "algorithm_containers": {"memory": "32m"},
                "preflight_image": "v6-it-sleep",
            },
            "network_isolation": {"probe_image": "curlimages/curl:8.11.1"},
        }
        cls.runtime = DockerRuntime(ctx, client=cls.client)
        cls.runtime.prepare()

    @classmethod
    def tearDownClass(cls):
        cls.runtime._remove_containers(cls.runtime._filters("algorithm"))
        cls.runtime.cleanup()
        cls.node.remove(force=True)
        cls.client.networks.get(cls.egress).remove()
        cls.tmp.cleanup()

    def _spec(self, run_id, image, step=AlgorithmStepType.FEDERATED_COMPUTE):
        for name in ("input", "output"):
            path = self.tasks / str(run_id) / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.touch()
        (self.tasks / "sessions/session000000001").mkdir(parents=True, exist_ok=True)
        return RunSpec(
            name=f"vantage6-run-{run_id}",
            image=image,
            step=step,
            env={},
            secret_env={},
            mounts=[
                MountSpec(TASK, f"{run_id}/output", "/app/vantage6/task/output"),
                MountSpec(TASK, f"{run_id}/input", "/app/vantage6/task/input", True),
                MountSpec(
                    TASK, "sessions/session000000001", "/app/vantage6/task/session"
                ),
            ],
            metadata=RunMetadata(
                run_id=run_id,
                task_id=run_id,
                task_parent_id=None,
                init_org_id=1,
                action=step,
                session_id=1,
            ),
            pull_policy=PullPolicy.IF_NOT_PRESENT,
        )

    def _wait_finished(self, name, timeout=60):
        deadline = time.time() + timeout
        while time.time() < deadline:
            run = next(r for r in self.runtime.list_runs() if r.name == name)
            if run.state.is_finished:
                return run
            time.sleep(1)
        self.fail(f"{name} did not finish")

    def test_preflight(self):
        with patch(
            "vantage6.node.runtime.docker.runtime.TASK_FILES_ROOT", str(self.tasks)
        ):
            ok, message = self.runtime.preflight()
        self.assertTrue(ok, message)

    def test_isolation(self):
        ok, message = self.runtime.verify_isolation()
        self.assertTrue(ok, message)

    def test_container_only_mounts_its_own_files(self):
        spec = self._spec(1, "v6-it-sleep")
        self.assertEqual(self.runtime.start_run(spec, Mock()), RunStatus.ACTIVE)
        container = self.runtime._get(spec.name)
        container.reload()
        self.assertEqual(
            sorted(m["Source"] for m in container.attrs["Mounts"]),
            sorted(
                str(self.tasks / p)
                for p in ("1/output", "1/input", "sessions/session000000001")
            ),
        )
        self.assertEqual(container.attrs["HostConfig"]["NetworkMode"], "none")
        self.runtime.remove_run(spec.name, 1)
        self.assertFalse(self.runtime.run_exists(spec.name))

    def test_federated_step_cannot_reach_the_internet(self):
        spec = self._spec(2, "v6-it-internet")
        self.runtime.start_run(spec, Mock())
        run = self._wait_finished(spec.name)
        self.assertEqual(run.state, RunState.FAILED)
        self.runtime.remove_run(spec.name, 2)

    def test_out_of_memory(self):
        spec = self._spec(3, "v6-it-oom")
        self.runtime.start_run(spec, Mock())
        run = self._wait_finished(spec.name)
        self.assertEqual(run.state, RunState.FAILED)
        self.assertEqual(run.reason, "OOMKilled")
        self.runtime.remove_run(spec.name, 3)


if __name__ == "__main__":
    unittest.main()
