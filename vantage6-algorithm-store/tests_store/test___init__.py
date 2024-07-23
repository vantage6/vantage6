import unittest
from unittest.mock import patch

from vantage6.algorithm.store import AlgorithmStoreApp
from vantage6.algorithm.store.model.policy import Policy
from vantage6.cli.context.algorithm_store import AlgorithmStoreContext
from vantage6.common.enum import StorePolicies


class TestAlgorithmStoreApp(unittest.TestCase):
    @patch("vantage6.algorithm.store.db.Policy")
    def test_setup_policies(self, policy_mock):
        # Create a mock configuration
        config = {
            "policies": {
                "policy1": "value1",
                "policy2": ["value2", "value3"],
            },
            "allow_localhost": False,
        }

        # Create an instance of AlgorithmStoreApp
        app = AlgorithmStoreApp({""})

        # Call the setup_policies method
        app.setup_policies(config)

        # Check that the Policy objects are created with the correct values
        policy_mock.assert_any_call(key="policy1", value="value1")
        policy_mock.assert_any_call(key="policy2", value="value2")
        policy_mock.assert_any_call(key="policy2", value="value3")

        # Check that the old policies are deleted
        policy_mock.delete.assert_called()

        # Check that the localhost servers are deleted
        app.db.Vantage6Server.get_localhost_servers.assert_called()

        # Check that the correct policies are added to the database
        self.assertEqual(
            app.db.Policy.save.call_args_list,
            [
                (("policy1", "value1"),),
                (("policy2", "value2"),),
                (("policy2", "value3"),),
            ],
        )


if __name__ == "__main__":
    unittest.main()
