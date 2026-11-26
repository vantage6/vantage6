"""
The Kubernetes objects created for an algorithm run must not change unintentionally:
a node that is upgraded while runs are active has to recognise their jobs.

``golden/kubernetes_jobs.json`` holds what the node created before the container
runtime abstraction. Regenerate it only for an intended change.
"""

import json
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kubernetes.client import ApiClient

from vantage6.common.enum import RunStatus

from tests_node.golden.cases import (
    CASES,
    DATABASES,
    ENV,
    make_client,
    make_ctx,
    make_run_io,
    task_info,
)
from vantage6.node.container.container_manager import ContainerManager
from vantage6.node.runtime.kubernetes.runtime import KubernetesRuntime

GOLDEN = json.loads((Path(__file__).parent / "golden/kubernetes_jobs.json").read_text())
CM = "vantage6.node.container.container_manager"


def build_objects(case: dict) -> dict:
    core, batch = MagicMock(), MagicMock()
    with (
        patch.dict(os.environ, ENV),
        patch("kubernetes.config.load_incluster_config"),
        patch("kubernetes.client.CoreV1Api", return_value=core),
        patch("kubernetes.client.BatchV1Api", return_value=batch),
        patch.object(
            ContainerManager, "_get_database_metadata", return_value=DATABASES
        ),
        patch(f"{CM}.RunIO", side_effect=make_run_io),
        patch.object(ContainerManager, "is_image_allowed", return_value=True),
        patch.object(ContainerManager, "is_running", return_value=False),
        patch.object(ContainerManager, "_validate_dataframes"),
        patch.object(ContainerManager, "_stream_logs"),
        patch.object(
            KubernetesRuntime,
            "_wait_until_pod_running",
            return_value=RunStatus.ACTIVE,
        ),
    ):
        ctx = make_ctx()
        manager = ContainerManager(ctx, make_client(), KubernetesRuntime(ctx))
        status = manager.run(
            run_id=case["run_id"],
            task_info=task_info(case),
            image="reg.example.org/algo:1",
            function_arguments=b"args",
            session_id=3,
            token=case["token"],
            databases_to_use=case["databases_to_use"],
            action=case["action"],
            on_status_change=MagicMock(),
        )
    assert status == RunStatus.ACTIVE, status
    api = ApiClient()
    return {
        "job": api.sanitize_for_serialization(
            batch.create_namespaced_job.call_args.kwargs["body"]
        ),
        "job_namespace": batch.create_namespaced_job.call_args.kwargs["namespace"],
        "secrets": [
            api.sanitize_for_serialization(c.kwargs["body"])
            for c in core.create_namespaced_secret.call_args_list
        ],
    }


class TestKubernetesJobGolden(unittest.TestCase):
    def test_objects_match_golden(self):
        for name, case in CASES.items():
            with self.subTest(name):
                actual = json.loads(json.dumps(build_objects(case), sort_keys=True))
                self.assertEqual(actual, GOLDEN[name])


if __name__ == "__main__":
    unittest.main()
