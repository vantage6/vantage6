import json
from unittest import TestCase

from vantage6.mock import MockNetwork
from vantage6.mock.server import MockServer


class TestMockServer(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.network = MockNetwork(
            module_name="test_algorithm", datasets=[], collaboration_id=1
        )
        self.server = MockServer(self.network)

    def test_initialization(self):
        """Test if server is properly initialized"""
        self.assertEqual(self.server.network.collaboration_id, 1)
        self.assertEqual(self.server.session_id, 1)
        self.assertEqual(self.server.study_id, 1)
        self.assertEqual(len(self.server.tasks), 0)
        self.assertEqual(len(self.server.runs), 0)
        self.assertEqual(len(self.server.results), 0)

    def test_save_result(self):
        """Test if results are properly saved"""
        test_result = {"test": "data"}
        result = self.server.save_result(test_result, task_id=1)

        self.assertEqual(len(self.server.results), 1)
        self.assertEqual(result["id"], 1)
        self.assertEqual(json.loads(result["result"]), test_result)
        self.assertEqual(result["task"]["id"], 1)

    def test_save_run(self):
        """Test if runs are properly saved"""
        test_args = {"arg1": "value1"}
        run = self.server.save_run(
            arguments=test_args, task_id=1, result_id=1, org_id=1
        )

        self.assertEqual(len(self.server.runs), 1)
        self.assertEqual(run["id"], 1)
        self.assertEqual(json.loads(run["arguments"]), test_args)
        self.assertEqual(run["task"]["id"], 1)
        self.assertEqual(run["results"]["id"], 1)
        self.assertEqual(run["status"], "completed")

    def test_save_task(self):
        """Test if tasks are properly saved"""
        test_databases = [{"name": "test_db", "uri": "test_uri"}]
        task = self.server.save_task(
            name="test_task",
            description="test description",
            databases=test_databases,
            init_organization_id=1,
        )

        self.assertEqual(len(self.server.tasks), 1)
        self.assertEqual(task["id"], 1)
        self.assertEqual(task["name"], "test_task")
        self.assertEqual(task["description"], "test description")
        self.assertEqual(task["databases"], test_databases)
        self.assertEqual(task["init_org"]["id"], 1)
        self.assertEqual(task["collaboration"]["id"], 1)
