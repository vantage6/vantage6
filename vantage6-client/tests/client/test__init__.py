import unittest
import uuid

from unittest.mock import patch, MagicMock
from vantage6.client import UserClient
from vantage6.common.encryption import DummyCryptor


class TestUserClient(unittest.TestCase):
    def setUp(self):
        self.dummy_uuid = str(uuid.uuid4())
        self.client_instance = UserClient(host="http://dummy_host", port=1234)
        self.client_instance.cryptor = DummyCryptor()
        self.client_instance.task = MagicMock()
        self.client_instance.task.get.return_value = {"status": "PENDING"}
        self.client_instance.request = MagicMock()
        self.client_instance.request.return_value = {
            "data": [
                {
                    "result": str(self.dummy_uuid),
                    "blob_storage_used": True,
                }
            ]
        }
        self.client_instance.request.status_code = 200

    @patch("requests.get")
    @patch("vantage6.client.UserClient.authenticate")
    @patch("vantage6.client.UserClient.setup_encryption")
    def test_wait_for_results(
        self, mock_setup_encryption, mock_authenticate, mock_requests_get
    ):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = (
            '{"key": "value"}'  # Ensure text attribute is set for logging
        )
        mock_response._decrypt_result = lambda: [{"key": "value"}]
        mock_requests_get.return_value.__enter__.return_value = mock_response

        mock_authenticate.return_value = "mock_token"
        mock_setup_encryption = DummyCryptor()
        mock_setup_encryption.return_value = True

        results = self.client_instance.wait_for_results(task_id=1, interval=0.1)
        mock_requests_get.assert_called_once_with(
            f"http://dummy_host:1234/api/blobstream/{self.dummy_uuid}",
            headers={"Content-Type": "application/octet-stream"},
            stream=True,
            timeout=300,
        )
        self.assertEqual(len(results), 1)


if __name__ == "__main__":
    unittest.main()
