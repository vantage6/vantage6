from azure.storage.blob import BlobServiceClient
import logging
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

class AzureStorageService:
    def __init__(self, connection_string: str, container_name: str):
        self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        self.container_name = container_name
        self.container_client = self.blob_service_client.get_container_client(container_name)


    def get_blob(self, blob_name: str) -> bytes:
        """
        Retrieve a blob from Azure Blob Storage.
        """
        log.debug(f"Retrieving blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        stream = blob_client.download_blob()
        return stream.readall()

    def store_blob(self, blob_name: str, data: bytes) -> None:
        """
        Store data as a blob in Azure Blob Storage.
        """
        log.debug(f"Storing blob: {blob_name} in container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def delete_blob(self, blob_name: str) -> None:
        """
        Delete a blob from Azure Blob Storage.
        """
        log.debug(f"Deleting blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        blob_client.delete_blob()