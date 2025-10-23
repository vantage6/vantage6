import base64
import json
import unittest
import uuid
from unittest.mock import MagicMock, patch

import jwt

from vantage6.common.globals import STRING_ENCODING

from vantage6.algorithm.client import AlgorithmClient


def encode_result(result_dict: dict) -> str:
    """Encode the result dictionary as a base64 string."""
    return base64.urlsafe_b64encode(json.dumps(result_dict).encode()).decode()


class TestAlgorithmClient(unittest.TestCase):
    def setUp(self):
        payload = {
            "sub": {
                "image": "dummy",
                "databases": [],
                "node_id": 1,
                "collaboration_id": 1,
            }
        }
        dummy_token = jwt.encode(payload, key="", algorithm=None)
        self.client = AlgorithmClient(
            token=dummy_token,
            server_url="http://dummy_host:1234",
        )
        self.client.parent = MagicMock()
        self.client.parent.request = MagicMock()
        self.client.parent.image = "mock_image"
        self.client.parent.collaboration_id = 1
        self.client.parent.databases = []
        self.client.parent.study_id = None
        self.client.parent.store_id = None
        self.client.generate_path_to = MagicMock(
            return_value="http://mock_blobstream_url"
        )
        self.client.parent.request.side_effect = [
            {"public_key": "mock_public_key"},  # For organization public key
            {"uuid": "mock_uuid"},  # For blobstream response
            {"task_id": 123},  # For task creation response
        ]
        self.client.log = MagicMock()

    @patch("requests.get")
    @patch("requests.post")
    @patch("vantage6.algorithm.client.serialize", return_value=b"serialized_arguments")
    def test_create_task(self, mock_serialize, mock_requests_post, mock_requests_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "uuid": "mock_uuid",
            "public_key": "mock_public_key",
            "task_id": 123,
        }
        mock_requests_post.return_value = mock_response

        mock_requests_get.return_value = mock_response

        arguments_data = {"myargument": "myvalue"}
        organizations = [1]
        method = "mock_method"
        result = self.client.task.create(
            arguments=arguments_data, organizations=organizations, method=method
        )

        self.assertEqual(
            result,
            {"uuid": "mock_uuid", "public_key": "mock_public_key", "task_id": 123},
        )
        mock_serialize.assert_called_once_with(arguments_data)

    @patch("vantage6.algorithm.client.AlgorithmClient._multi_page_request")
    def test_result_from_task(self, mock_multi_page_request):
        mock_multi_page_request.return_value = [
            {
                "result": encode_result({"foo": "bar"}),  # base64 for '{"foo": "bar"}'
                "blob_storage_used": None,
            }
        ]

        results = self.client.result.from_task(task_id=1)
        self.assertEqual(results[0], {"foo": "bar"})

    @patch("vantage6.algorithm.client.AlgorithmClient._multi_page_request")
    @patch(
        "vantage6.common.client.client_base.ClientBase._download_run_data_from_server"
    )
    def test_result_from_task_azure(
        self, mock_download_run_data, mock_multi_page_request
    ):
        with (
            patch.object(
                self.client.result.parent, "_multi_page_request"
            ) as mock_multi_page_request,
            patch.object(
                self.client.result.parent, "_download_run_data_from_server"
            ) as mock_download_run_data,
        ):
            # Simulate a result where blob_storage_used is True
            mock_multi_page_request.return_value = [
                {
                    "result": str(uuid.uuid4()),
                    "blob_storage_used": True,
                }
            ]
            expected_value = {"foo": "bar"}
            mock_download_run_data.return_value = json.dumps(expected_value).encode(
                STRING_ENCODING
            )
            results = self.client.result.from_task(task_id=1)
            self.assertEqual(results[0], expected_value)

    @patch("vantage6.algorithm.client.AlgorithmClient._multi_page_request")
    def test_result_from_task_relational(self, mock_multi_page_request):
        mock_multi_page_request.return_value = [
            {
                "result": encode_result({"foo": "bar"}),
                "blob_storage_used": False,
            },
        ]

        results = self.client.result.from_task(task_id=1)

        self.assertEqual(results[0], {"foo": "bar"})


if __name__ == "__main__":
    unittest.main()
