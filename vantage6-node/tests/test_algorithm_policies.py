import unittest
from unittest.mock import MagicMock, patch

from vantage6.common.globals import NodePolicy

from vantage6.node import Node


class TestCheckAlgorithmPolicies(unittest.TestCase):
    """
    Tests for Node.check_algorithm_policies().

    Node.__init__ connects to the server and Docker, so these tests bypass it (via
    __new__) and set up only the attributes the check reads: `config` and `log`.
    """

    def _node(self, config: dict) -> Node:
        node = Node.__new__(Node)
        node.config = config
        node.log = MagicMock()
        return node

    def _assert_exits(self, config: dict):
        node = self._node(config)
        with (
            patch("vantage6.node.sys.exit", side_effect=SystemExit(1)) as mock_exit,
            self.assertRaises(SystemExit),
        ):
            node.check_algorithm_policies()
        mock_exit.assert_called_once_with(1)
        node.log.error.assert_called_once()

    def _assert_starts(self, config: dict) -> Node:
        node = self._node(config)
        with patch("vantage6.node.sys.exit") as mock_exit:
            node.check_algorithm_policies()
        mock_exit.assert_not_called()
        return node

    def test_production_without_policies_exits(self):
        self._assert_exits({"production": True})

    def test_production_is_default(self):
        self._assert_exits({})

    def test_production_with_empty_policies_exits(self):
        self._assert_exits(
            {
                "policies": {
                    NodePolicy.ALLOWED_ALGORITHMS: [],
                    NodePolicy.ALLOWED_ALGORITHM_STORES: [],
                    NodePolicy.ALLOWED_USERS: [1],
                }
            }
        )

    def test_production_with_allowed_algorithms_starts(self):
        node = self._assert_starts(
            {
                "production": True,
                "policies": {NodePolicy.ALLOWED_ALGORITHMS: ["^some/image$"]},
            }
        )
        node.log.warning.assert_not_called()

    def test_production_with_allowed_stores_starts(self):
        node = self._assert_starts(
            {
                "production": True,
                "policies": {
                    NodePolicy.ALLOWED_ALGORITHM_STORES: ["https://store.example"]
                },
            }
        )
        node.log.warning.assert_not_called()

    def test_non_production_without_policies_warns(self):
        node = self._assert_starts({"production": False})
        node.log.warning.assert_called()
        node.log.error.assert_not_called()
