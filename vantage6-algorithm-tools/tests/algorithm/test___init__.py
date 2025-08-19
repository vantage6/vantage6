import unittest
import os
import sys
import json
sys.path.append(os.path.join(os.path.dirname(__file__),'../../'))
from unittest.mock import patch, MagicMock
from vantage6.algorithm.client import AlgorithmClient
from vantage6.common.globals import DataStorageUsed


class TestAlgorithmClient(unittest.TestCase):
    
    def setUp(self):
        self.client = AlgorithmClient(token="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOnsiaW1hZ2UiOiJtb2NrX2ltYWdlIiwiZGF0YWJhc2VzIjpbXSwibm9kZV9pZCI6MSwiY29sbGFib3JhdGlvbl9pZCI6MSwic3R1ZHlfaWQiOm51bGwsInN0b3JlX2lkIjpudWxsLCJvcmdhbml6YXRpb25faWQiOjF9LCJleHAiOjE2ODk5OTk5OTl9.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c", host="http://dummy_host", port=1234)
        self.client.parent = MagicMock()
        self.client.parent.request = MagicMock()
        self.client.parent.image = "mock_image"
        self.client.parent.collaboration_id = 1
        self.client.parent.databases = []
        self.client.parent.study_id = None
        self.client.parent.store_id = None
        self.client.generate_path_to = MagicMock(return_value="http://mock_blobstream_url")
        self.client.parent.request.side_effect = [
            {"public_key": "mock_public_key"},  # For organization public key
            {"uuid": "mock_uuid"},             # For blobstream response
            {"task_id": 123}                    # For task creation response
        ]
        self.client.log = MagicMock()

    @patch('requests.get')
    @patch('requests.post')
    @patch('vantage6.algorithm.client.serialize', return_value=b'serialized_input')
    def test_create_task(self, mock_serialize, mock_requests_post, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"uuid": "mock_uuid", "public_key": "mock_public_key", "task_id": 123}
        mock_requests_post.return_value = mock_response
        
        mock_requests_get.return_value = mock_response

        input_data = {"method": "mock_method", "args": [1, 2, 3]}
        organizations = [1]
        result = self.client.task.create(input_=input_data, organizations=organizations)

        self.assertEqual(result, {"uuid": "mock_uuid", "public_key": "mock_public_key", "task_id": 123})
        mock_serialize.assert_called_once_with(input_data)

    @patch('vantage6.algorithm.client.AlgorithmClient._multi_page_request')
    def test_result_from_task(self, mock_multi_page_request):
        mock_multi_page_request.return_value = [
            {
                "result": "eyJmb28iOiAiYmFyIn0=",  # base64 for '{"foo": "bar"}'
                "data_storage_used": None
            },
            {
                "result": None,
                "data_storage_used": None
            }
        ]

        results = self.client.result.from_task(task_id=1)

        self.assertEqual(results[0], {"foo": "bar"})
            
    def test_result_from_task_azure(self):
        with patch.object(self.client.result.parent, 'download_run_data_from_server') as mock_download_run_data_from_server, \
            patch.object(self.client.result.parent, '_multi_page_request') as mock_multi_page_request:
            # Simulate a result where data_storage_used is 'azure'
            mock_multi_page_request.return_value = [
                {
                    "result": "123e4567-e89b-12d3-a456-426614174000",
                    "data_storage_used": DataStorageUsed.AZURE.value
                },
                {
                    "result": None,
                    "data_storage_used": DataStorageUsed.AZURE.value
                }
            ]
            expected_value = {"foo": "bar"}
            mock_download_run_data_from_server.return_value = json.dumps(expected_value).encode("utf-8")
            results = self.client.result.from_task(task_id=1)

            self.assertEqual(results[0], {"foo": "bar"})

    def test_result_from_task_relational(self):
        with patch.object(self.client.result.parent, '_multi_page_request') as mock_multi_page_request:
            mock_multi_page_request.return_value = [
                {
                    "result": "eyJmb28iOiAiYmFyIn0=",  # base64 for '{"foo": "bar"}'
                    "data_storage_used": DataStorageUsed.RELATIONAL.value
                },
                {
                    "result": None,
                    "data_storage_used": DataStorageUsed.RELATIONAL.value
                }
            ]

            results = self.client.result.from_task(task_id=1)

            self.assertEqual(results[0], {"foo": "bar"})

if __name__ == "__main__":
     unittest.main()
