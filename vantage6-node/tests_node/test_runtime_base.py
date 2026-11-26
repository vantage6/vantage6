import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vantage6.common.enum import AlgorithmStepType

from vantage6.node.runtime import RUNTIMES, get_runtime, runtime_name
from vantage6.node.runtime.base import RunMetadata

GOLDEN = json.loads((Path(__file__).parent / "golden/kubernetes_jobs.json").read_text())


class TestRunMetadata(unittest.TestCase):
    def test_round_trip_of_existing_job_annotations(self):
        for name, case in GOLDEN.items():
            with self.subTest(name):
                annotations = case["job"]["metadata"]["annotations"]
                self.assertEqual(
                    RunMetadata.from_dict(annotations).to_dict(), annotations
                )

    def test_parent_and_dataframe(self):
        metadata = RunMetadata(
            run_id=1,
            task_id=2,
            task_parent_id=3,
            init_org_id=4,
            action=AlgorithmStepType.DATA_EXTRACTION,
            session_id=5,
            df_name="df",
            df_id="6",
            df_label="db",
        )
        self.assertEqual(RunMetadata.from_dict(metadata.to_dict()), metadata)


class TestRuntimeRegistry(unittest.TestCase):
    def _ctx(self, runtime: str | None) -> MagicMock:
        ctx = MagicMock()
        ctx.config = {} if runtime is None else {"container_runtime": runtime}
        return ctx

    def test_kubernetes_is_the_default(self):
        self.assertEqual(runtime_name(self._ctx(None)), "kubernetes")

    def test_unknown_runtime_is_refused(self):
        with self.assertRaises(ValueError):
            get_runtime(self._ctx("podman"))

    def test_runtime_is_built_from_the_registry(self):
        runtime_cls = MagicMock()
        ctx = self._ctx("docker")
        with patch.dict(RUNTIMES, {"docker": lambda: runtime_cls}):
            self.assertIs(get_runtime(ctx), runtime_cls.return_value)
        runtime_cls.assert_called_once_with(ctx)


if __name__ == "__main__":
    unittest.main()
