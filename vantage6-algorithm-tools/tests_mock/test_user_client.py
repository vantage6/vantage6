from unittest import TestCase
from unittest.mock import MagicMock, patch

import pandas as pd

from vantage6.client import UserClient

from vantage6.mock import MockNetwork
from vantage6.mock.client import MockUserClient


class TestMockUserClient(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.data1 = pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})
        self.data2 = pd.DataFrame({"id": [4, 5, 6], "value": [40, 50, 60]})

        with patch("vantage6.mock.node.import_module", return_value=MagicMock()):
            self.network = MockNetwork(
                module_name="test_algorithm",
                datasets=[
                    {"label_1": {"database": self.data1, "db_type": "csv"}},
                    {"label_2": {"database": self.data2, "db_type": "csv"}},
                ],
            )
        self.client = self.network.user_client

    def test_client_initialization(self):
        """Test if client is properly initialized"""
        self.assertIsInstance(self.client, MockUserClient)
        self.assertEqual(self.client.organization_id, 0)

    def test_same_attributes_as_user_client(self):
        """Test if the MockUserClient has the same attributes as the UserClient"""
        # Get all attributes from the real UserClient
        user_client_attrs = set(dir(UserClient("", "")))
        mock_client_attrs = set(dir(self.client))

        # The user client attributes need to be a subset of the mock client attributes
        self.assertTrue(user_client_attrs.issubset(mock_client_attrs))
