import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from vantage6.common.task_status import TaskStatus


class TesRelayManagerTests(unittest.TestCase):
    def _ctx(self):
        return SimpleNamespace(
            name="test-node",
            config={
                "tes_relay": {
                    "enabled": True,
                    "tes_endpoint": "http://localhost:5034",
                    "tags": {"project": "Testing", "tres": "DEMO"},
                    "dare": {"project_id": 1},
                    "databases_map": {"default": "/datasets/default.csv"},
                    "command": None,
                    "keycloak": {
                        "token_url": "http://localhost:8085/realms/Dare-Control/protocol/openid-connect/token",
                        "client_id": "cid",
                        "client_secret": "sec",
                        "username": "u",
                        "password": "p",
                    },
                    "poll_in_background": False,
                }
            },
        )

    @patch("vantage6.node.tes_relay.manager.DareSubmissionLayerClient")
    def test_run_and_poll_complete(self, MockSubmissionClient):
        from vantage6.node.tes_relay.manager import TesRelayManager

        sub = MockSubmissionClient.return_value
        sub.resolve_submission_bucket.return_value = "bucket"
        sub.tes.create_task.return_value = "123"
        sub.tes.get_task.return_value = {
            "id": "123",
            "state": "COMPLETE",
            "outputs": [],
        }

        mgr = TesRelayManager(
            ctx=self._ctx(),
            isolated_network_mgr=None,
            vpn_manager=None,
            tasks_dir=Path("/tmp"),
            client=None,
            proxy=None,
        )

        status, vpn_ports = mgr.run(
            run_id=42,
            task_info={
                "id": 7,
                "job_id": 9,
                "databases": [{"label": "default"}],
            },
            image="some-image:tag",
            docker_input='{"method":"average"}',
            tmp_vol_name="tmp",
            token="tok",
            databases_to_use=[],
            socketIO=None,
        )

        self.assertEqual(status, TaskStatus.ACTIVE)
        self.assertIsNone(vpn_ports)
        sub.upload_to_minio.assert_called()
        sub.tes.create_task.assert_called()

        mgr.poll_once()
        res = mgr.get_result(timeout=1)
        self.assertEqual(res.status, TaskStatus.COMPLETED)
        payload = json.loads(res.data.decode("utf-8"))
        self.assertEqual(payload["tes"]["id"], "123")

    @patch("vantage6.node.tes_relay.manager.DareSubmissionLayerClient")
    def test_kill_tasks_requests_cancel(self, MockSubmissionClient):
        from vantage6.node.tes_relay.manager import TesRelayManager

        sub = MockSubmissionClient.return_value
        sub.resolve_submission_bucket.return_value = "bucket"
        sub.tes.create_task.return_value = "999"

        mgr = TesRelayManager(
            ctx=self._ctx(),
            isolated_network_mgr=None,
            vpn_manager=None,
            tasks_dir=Path("/tmp"),
            client=None,
            proxy=None,
        )

        mgr.run(
            run_id=1,
            task_info={
                "id": 2,
                "job_id": 3,
                "databases": [{"label": "default"}],
            },
            image="img",
            docker_input="{}",
            tmp_vol_name="tmp",
            token="tok",
            databases_to_use=[],
            socketIO=None,
        )
        killed = mgr.kill_tasks(
            org_id=5,
            kill_list=[{"run_id": 1, "organization_id": 5}],
        )
        self.assertEqual(len(killed), 1)
        sub.tes.cancel_task.assert_called_with("999")


if __name__ == "__main__":
    unittest.main()
