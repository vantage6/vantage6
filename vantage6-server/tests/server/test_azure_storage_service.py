import logging
import unittest
from unittest.mock import MagicMock, patch
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient
from vantage6.server.service.azure_storage_service import AzureStorageService

class TestAzureStorageService(unittest.TestCase):

    # @patch('azure.identity.ClientSecretCredential')
    # @patch('azure.storage.blob.BlobServiceClient')
    # def test_initialization(self, mock_blob_service_client, mock_credential):
    #     tenant_id = "tentant"
    #     client_id = "test_client_id"
    #     client_secret = "test_client_secret"
    #     storage_account_name = "test_storage_account"
    #     container_name = "test_container"

    #     service = AzureStorageService(tenant_id, client_id, client_secret, storage_account_name, container_name)
    #     self.assertEqual(service.container_name, container_name)

    # @patch('azure.storage.blob.BlobClient')
    # @patch('azure.storage.blob.BlobServiceClient')
    # def test_get_blob(self, mock_blob_service_client, mock_blob_client):
    #     mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    #     mock_blob_client.download_blob.return_value.readall.return_value = b"test_data"

    #     service = AzureStorageService("tenant", "client", "secret", "account", "container")
    #     service.blob_service_client = mock_blob_service_client.return_value

    #     result = service.get_blob("test_blob")
    #     self.assertEqual(result, b"test_data")
    #     mock_blob_client.download_blob.assert_called_once()

    # @patch('azure.storage.blob.BlobClient')
    # @patch('azure.storage.blob.BlobServiceClient')
    # def test_store_blob(self, mock_blob_service_client, mock_blob_client):
    #     mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client

    #     service = AzureStorageService("tenant", "client", "secret", "account", "container")
    #     service.blob_service_client = mock_blob_service_client.return_value

    #     service.store_blob("test_blob", b"test_data")
    #     mock_blob_client.upload_blob.assert_called_once_with(b"test_data", overwrite=True)

    # @patch('azure.storage.blob.BlobClient')
    # @patch('azure.storage.blob.BlobServiceClient')
    # def test_delete_blob(self, mock_blob_service_client, mock_blob_client):
    #     mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client

    #     service = AzureStorageService("tenant", "client", "secret", "account", "container")
    #     service.blob_service_client = mock_blob_service_client.return_value

    #     service.delete_blob("test_blob")
    #     mock_blob_client.delete_blob.assert_called_once()

    # @patch('azure.storage.blob.BlobClient')
    # @patch('azure.storage.blob.BlobServiceClient')
    # def test_stream_blob(self, mock_blob_service_client, mock_blob_client):
    #     mock_blob_service_client.return_value.get_blob_client.return_value = mock_blob_client
    #     mock_blob_client.download_blob.return_value = MagicMock()

    #     service = AzureStorageService("tenant", "client", "secret", "account", "container")
    #     service.blob_service_client = mock_blob_service_client.return_value

    #     result = service.stream_blob("test_blob")
    #     self.assertEqual(result, mock_blob_client.download_blob.return_value)
    #     mock_blob_client.download_blob.assert_called_once()

if __name__ == "__main__":
    unittest.main()
