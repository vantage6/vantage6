import unittest
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'../../'))
from unittest.mock import patch, MagicMock
from vantage6.client import UserClient
from vantage6.common.encryption import DummyCryptor


class TestUserClient(unittest.TestCase):
    @patch('requests.get')
    @patch('vantage6.client.UserClient.authenticate')
    @patch('vantage6.client.UserClient.setup_encryption')
    def test_retrieve_results(self, mock_setup_encryption, mock_authenticate, mock_requests_get):
      
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'{"key": "value"}']
        mock_response.text = '{"key": "value"}'  # Ensure text attribute is set for logging
        mock_response._decrypt_result = lambda: [{"key": "value"}]
        mock_requests_get.return_value.__enter__.return_value = mock_response
        
        mock_authenticate.return_value= "mock_token"
        mock_setup_encryption = DummyCryptor()
        mock_setup_encryption.return_value = True

        # Create an instance of UserClient
        client_instance = UserClient(host="http://dummy_host", port=1234)

        # Initialize the cryptor attribute
        client_instance.cryptor = DummyCryptor()

        # Mock the task.get method
        client_instance.task = MagicMock()
        client_instance.task.get.return_value = {"status": "PENDING"}

        # Mock the request method
        client_instance.request = MagicMock()
        client_instance.request.return_value = {
            "data": [
                {"result": "123e4567-e89b-12d3-a456-426614174000", "data_storage_used": "Azure"}
            ]
        }
        client_instance.request.status_code = 200
      
        # Call the method under test
        results = client_instance.retrieve_results(task_id=1, interval=0.1, )
        print(results)
        # Assertions
        
        self.assertEqual(len(results), 1)



if __name__ == "__main__":
     unittest.main()