from unittest import TestCase
from unittest.mock import MagicMock, patch

import pandas as pd

from vantage6.algorithm.data_extraction.mock_extract import MockDatabaseType
from vantage6.mock import MockNetwork
from vantage6.mock.client import MockAlgorithmClient, MockUserClient
from vantage6.mock.node import MockNode
from vantage6.mock.server import MockServer

TEST_ALGORITHM_NAME = "test_algorithm"
DB_LABEL_1 = "label_1"
DB_LABEL_2 = "label_2"
MOCK_DATA_CSV = "mock_data.csv"


class TestMockNetworkDataframe(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        # Create a simple mock network with 2 nodes
        self.data1 = pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 30]})
        self.data2 = pd.DataFrame({"id": [4, 5, 6], "value": [40, 50, 60]})

        with patch("vantage6.mock.node.import_module", return_value=MagicMock()):
            self.network = MockNetwork(
                module_name=TEST_ALGORITHM_NAME,
                datasets=[
                    {
                        DB_LABEL_1: {
                            "database": self.data1,
                            "db_type": MockDatabaseType.CSV.value,
                        }
                    },
                    {
                        DB_LABEL_2: {
                            "database": self.data2,
                            "db_type": MockDatabaseType.CSV.value,
                        }
                    },
                ],
            )

    def test_network_initialization(self):
        """Test if network is properly initialized"""
        self.assertEqual(len(self.network.nodes), 2)
        self.assertEqual(self.network.module_name, TEST_ALGORITHM_NAME)

        # Check if data is properly assigned to nodes
        node1_data = self.network.nodes[0].dataframes[DB_LABEL_1]
        node2_data = self.network.nodes[1].dataframes[DB_LABEL_2]

        pd.testing.assert_frame_equal(node1_data, self.data1)
        pd.testing.assert_frame_equal(node2_data, self.data2)

    def test_attributes(self):
        """Test if properties are properly initialized"""
        # Check the type of the server
        self.assertIsInstance(self.network.server, MockServer)
        self.assertIsInstance(self.network.user_client, MockUserClient)
        self.assertIsInstance(self.network.algorithm_client, MockAlgorithmClient)

        self.assertEqual(len(self.network.nodes), 2)
        self.assertIsInstance(self.network.nodes[0], MockNode)
        self.assertIsInstance(self.network.nodes[1], MockNode)

        self.assertEqual(self.network.module_name, TEST_ALGORITHM_NAME)
        self.assertEqual(self.network.collaboration_id, 1)

    def test_properties(self):
        """Test if properties are properly initialized"""
        self.assertEqual(len(self.network.organization_ids), 2)
        self.assertEqual(len(self.network.node_ids), 2)

    def test_get_node(self):
        """Test if get_node is properly initialized"""
        self.assertIsInstance(self.network.get_node(1), MockNode)
        self.assertIsInstance(self.network.get_node(2), MockNode)

    def test_server_initialization(self):
        """Test if server is properly initialized"""
        self.assertEqual(len(self.network.server.tasks), 0)
        self.assertEqual(len(self.network.server.runs), 0)
        self.assertEqual(len(self.network.server.results), 0)

    def test_node_initialization(self):
        """Test if node is properly initialized"""
        self.assertEqual(len(self.network.nodes), 2)
        self.assertEqual(self.network.nodes[0].id_, 1)
        self.assertEqual(self.network.nodes[1].id_, 2)
        self.assertEqual(self.network.nodes[0].organization_id, 1)
        self.assertEqual(self.network.nodes[1].organization_id, 2)
        self.assertEqual(self.network.nodes[0].collaboration_id, 1)
        self.assertEqual(self.network.nodes[1].collaboration_id, 1)


class TestMockNetworkURI(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        with patch("vantage6.mock.node.import_module", return_value=MagicMock()):
            self.network = MockNetwork(
                module_name=TEST_ALGORITHM_NAME,
                datasets=[
                    {
                        DB_LABEL_1: {
                            "database": MOCK_DATA_CSV,
                            "db_type": MockDatabaseType.CSV.value,
                        }
                    }
                ],
            )

    def test_network_initialization(self):
        """Test if network is properly initialized"""
        self.assertEqual(len(self.network.nodes), 1)
        self.assertEqual(len(self.network.nodes[0].dataframes), 0)
        self.assertEqual(
            self.network.nodes[0].datasets[DB_LABEL_1]["database"], MOCK_DATA_CSV
        )

    def test_node_initialization(self):
        """Test if node is properly initialized"""
        self.assertEqual(len(self.network.nodes), 1)
        self.assertEqual(self.network.nodes[0].id_, 1)
        self.assertEqual(self.network.nodes[0].organization_id, 1)
        self.assertEqual(self.network.nodes[0].collaboration_id, 1)
