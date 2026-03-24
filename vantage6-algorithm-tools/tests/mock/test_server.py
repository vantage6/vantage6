import json
from unittest import TestCase

from vantage6.algorithm.mock import MockNetwork
from vantage6.algorithm.mock.hq import MockHQ


class TestMockHQ(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.network = MockNetwork(
            module_name="test_algorithm",
            datasets=[
                # {
                #     "dataset_1": {
                #         "database": pd.DataFrame(
                #             {"id": [1, 2, 3], "value": [10, 20, 30]}
                #         ),
                #     }
                # }
            ],
            collaboration_id=1,
        )
        self.hq = MockHQ(self.network)

    def test_initialization(self):
        """Test if HQ is properly initialized"""
        self.assertEqual(self.hq.network.collaboration_id, 1)
        self.assertEqual(self.hq.session_id, 1)
        self.assertEqual(self.hq.study_id, 1)
        self.assertEqual(len(self.hq.tasks), 0)
        self.assertEqual(len(self.hq.runs), 0)
        self.assertEqual(len(self.hq.results), 0)

    def test_save_result(self):
        """Test if results are properly saved"""
        test_result = {"test": "data"}
        result = self.hq.save_result(test_result, task_id=1)

        self.assertEqual(len(self.hq.results), 1)
        self.assertEqual(result["id"], 1)
        self.assertEqual(json.loads(result["result"]), test_result)
        self.assertEqual(result["task"]["id"], 1)

    def test_save_run(self):
        """Test if runs are properly saved"""
        test_args = {"arg1": "value1"}
        run = self.hq.save_run(arguments=test_args, task_id=1, result_id=1, org_id=1)

        self.assertEqual(len(self.hq.runs), 1)
        self.assertEqual(run["id"], 1)
        self.assertEqual(json.loads(run["arguments"]), test_args)
        self.assertEqual(run["task"]["id"], 1)
        self.assertEqual(run["results"]["id"], 1)
        self.assertEqual(run["status"], "completed")

    def test_save_task(self):
        """Test if tasks are properly saved"""
        test_databases = [{"name": "test_db", "uri": "test_uri"}]
        task = self.hq.save_task(
            name="test_task",
            description="test description",
            databases=test_databases,
            init_organization_id=1,
        )

        self.assertEqual(len(self.hq.tasks), 1)
        self.assertEqual(task["id"], 1)
        self.assertEqual(task["name"], "test_task")
        self.assertEqual(task["description"], "test description")
        self.assertEqual(task["databases"], test_databases)
        self.assertEqual(task["init_org"]["id"], 1)
        self.assertEqual(task["collaboration"]["id"], 1)
