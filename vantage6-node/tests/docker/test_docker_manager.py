import unittest
from unittest.mock import MagicMock, patch, call
from pathlib import Path

from vantage6.node.docker.docker_manager import DockerManager, KilledRun, DockerTaskManager
from vantage6.node.docker.vpn_manager import VPNManager
from vantage6.node.docker.squid import Squid
from vantage6.common.client.node_client import NodeClient

class DummyTask:
    def __init__(self, run_id=1, task_id=2, parent_id=3):
        self.run_id = run_id
        self.task_id = task_id
        self.parent_id = parent_id
        self.cleaned = False
        self.docker_task_manager = object.__new__(DockerTaskManager)
        self.cleanup = self.docker_task_manager.cleanup
        self.docker_task_manager.log = MagicMock()
        self.container = MagicMock()
        self.helper_container = MagicMock()
        self.docker_task_manager.container = self.container
        self.docker_task_manager.helper_container = self.helper_container
        self.container.name = "dummy_container"
        self.helper_container.name = "dummy_helper_container"


class DummyContext:
    docker_volume_name = "dummy"
    config = {}
    name = "dummy"
    docker_container_name = "dummy"
    databases = []


class TestDockerManagerCleanup(unittest.TestCase):
    @patch("vantage6.node.docker.task_manager.DockerTaskManager")
    def setUp(self, mock_docker_manager):
        self.vpn_mgr = MagicMock(spec=VPNManager)
        self.tasks_dir = Path("/tmp")
        self.client = MagicMock(spec=NodeClient)
        self.proxy = MagicMock(spec=Squid)
        self.ctx = DummyContext()
        self.network_mgr = MagicMock()
        self.ctx.network_manager = self.network_mgr

        # Add missing variables
        self.docker_manager = DockerManager(
            ctx=self.ctx,
            isolated_network_mgr=self.network_mgr,
            vpn_manager=self.vpn_mgr,
            tasks_dir=self.tasks_dir,
            client=self.client,
            proxy=self.proxy,
        )
        self.docker_manager.active_tasks = [DummyTask(run_id=1, task_id=2, parent_id=3), DummyTask(run_id=4, task_id=5, parent_id=6)]
        self.docker_manager.linked_services = ["service1", "service2"]
        self.docker_manager.node_container_name = "node_container"

        # If you need DockerTaskManager for other tests, initialize it here as well
        self.docker_task_manager = object.__new__(DockerTaskManager)
        self.docker_task_manager.active_tasks = [DummyTask(run_id=1, task_id=2, parent_id=3), DummyTask(run_id=4, task_id=5, parent_id=6)]


    def test_cleanup(self):
        # Call cleanup
        self.docker_manager.cleanup()

        # All active tasks should be cleaned up
        for task in self.docker_manager.active_tasks:
            self.assertTrue(getattr(task, "cleaned", True))

        # Network manager should disconnect linked services and node container
        self.network_mgr.disconnect.assert_has_calls([
            call("service1"),
            call("service2"),
            call("node_container"),
        ], any_order=True)

        # Network manager should delete the network
        self.network_mgr.delete.assert_called_once_with(kill_containers=True)
        
if __name__ == "__main__":
    unittest.main()
