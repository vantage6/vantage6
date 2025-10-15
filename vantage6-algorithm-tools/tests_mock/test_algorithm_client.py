from unittest import TestCase

from vantage6.algorithm.client import AlgorithmClient
from vantage6.mock import MockNetwork
from vantage6.mock.client import MockAlgorithmClient

TEST_ALGORITHM_NAME = "test_algorithm"

class TestMockAlgorithmClient(TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.network = MockNetwork(
            module_name=TEST_ALGORITHM_NAME, datasets=[], collaboration_id=1
        )
        self.client = MockAlgorithmClient(self.network)

    def test_client_initialization(self):
        """Test if client is properly initialized"""
        self.assertIsInstance(self.client, MockAlgorithmClient)
        self.assertEqual(self.client.network.collaboration_id, 1)
        self.assertEqual(self.client.network.module_name, TEST_ALGORITHM_NAME)

    def test_same_attributes_as_algorithm_client(self):
        """Test if the MockAlgorithmClient has the same attributes as the AlgorithmClient"""
        from unittest.mock import patch

        # Mock data that jwt.decode would return
        mock_jwt_data = {
            "sub": {
                "image": "test_image",
                "databases": [],
                "node_id": 1,
                "organization_id": 1,
                "collaboration_id": 1,
                "study_id": 1,
                "store_id": 1,
                "session_id": 1,
            }
        }

        # Patch jwt.decode to return our mock data
        with patch("jwt.decode", return_value=mock_jwt_data):
            # Get all attributes from the real AlgorithmClient
            algorithm_client_attrs = set(
                dir(AlgorithmClient("dummy_token", "http://test.com"))
            )
            mock_client_attrs = set(dir(self.client))

            print(algorithm_client_attrs - mock_client_attrs)

            # The algorithm client attributes need to be a subset of the mock client attributes
            self.assertTrue(algorithm_client_attrs.issubset(mock_client_attrs))
