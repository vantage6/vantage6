import unittest
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__),'../../'))
from unittest.mock import patch, MagicMock
from vantage6.algorithm.client import AlgorithmClient


class TestAlgorithmClient(unittest.TestCase):
    @patch('requests.get')
    @patch('time.sleep', return_value=None)
    @patch('vantage6.common.task_status.has_task_finished', side_effect=[False, True])
    def test_wait_for_results(self, mock_has_task_finished, mock_sleep, mock_requests_get):
        # Mock the response from the server
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'{"key": "value"}']
        mock_response.text = '{"key": "value"}'  # Ensure text attribute is set for logging
        mock_requests_get.return_value.__enter__.return_value = mock_response

        # Create an instance of AlgorithmClient
        valid_mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOnsibmFtZSI6Ik1vY2sgVXNlciIsImlkIjoxMjN9LCJleHAiOjE2ODk5OTk5OTl9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        client_instance = AlgorithmClient(token=valid_mock_token, host="http://dummy_host", port=1234)

        # Mock the task.get method
        client_instance.task = MagicMock()
        client_instance.task.get.return_value = {"status": "PENDING"}

        # Mock the request method
        client_instance.request = MagicMock()
        client_instance.request.return_value = {"data": [{"result": "123e4567-e89b-12d3-a456-426614174000"}]}
        client_instance.request.status_code = 200
      

        # Call the method under test
        results = client_instance.wait_for_results(task_id=1, interval=0.1)
        print(results)
        # Assertions
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0], {"key": "value"})

    @patch('requests.get')
    @patch('requests.post')
    @patch('vantage6.algorithm.client.serialize', return_value=b'serialized_input')
    def test_create_task(self, mock_serialize, mock_requests_post, mock_requests_get):
        # Mock parent attributes and methods
        mock_parent = MagicMock()
        mock_parent.request.side_effect = [
            {"public_key": "mock_public_key"},  # For organization public key
            {"uuid": "mock_uuid"},             # For resultstream response
            {"task_id": 123}                    # For task creation response
        ]
        mock_parent.image = "mock_image"
        mock_parent.collaboration_id = 1
        mock_parent.databases = []
        mock_parent.study_id = None
        mock_parent.store_id = None
        mock_parent.token = "mock_token"
        mock_parent.generate_path_to.return_value = "http://mock_resultstream_url"

        # Create an instance of AlgorithmClient with the mocked parent
        valid_mock_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOnsibmFtZSI6Ik1vY2sgVXNlciIsImlkIjoxMjN9LCJleHAiOjE2ODk5OTk5OTl9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        client_instance = AlgorithmClient(token=valid_mock_token, host="http://dummy_host", port=1234)
        client_instance.parent = mock_parent

        # Mock the response from requests.post
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uuid": "mock_uuid", "public_key": "mock_public_key", "task_id": 123}
        mock_requests_post.return_value = mock_response
        
        # Mock the response from requests.get
        mock_requests_get.return_value = mock_response

        # Call the method under test
        input_data = {"method": "mock_method", "args": [1, 2, 3]}
        organizations = [1]
        result = client_instance.task.create(input_=input_data, organizations=organizations)

        # Assertions
        self.assertEqual(result, {"uuid": "mock_uuid", "public_key": "mock_public_key", "task_id": 123})
        mock_serialize.assert_called_once_with(input_data)


if __name__ == "__main__":
     unittest.main()
