from azure.storage.blob import BlobServiceClient
import logging
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

class AzureStorageService:
    def __init__(self, container_name:str, blob_service_client:BlobServiceClient = None, connection_string: str = None):
        self.container_name = container_name

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        elif blob_service_client:
            self.blob_service_client = blob_service_client
        else:
            raise ValueError("Either 'connection_string' or 'blob_service_client' must be provided.")            

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
        log.debug(f"Storing blob: {blob_name} in container: {self.container_name} (size: {len(data)} bytes)")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        try:
            blob_client.upload_blob(data, overwrite=True)
        except Exception as e:
            log.error(f"Failed to upload blob '{blob_name}': {e}")
            raise RuntimeError(f"Failed to upload blob '{blob_name}': {e}")

    def delete_blob(self, blob_name: str) -> None:
        """
        Delete a blob from Azure Blob Storage.
        """
        log.debug(f"Deleting blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        blob_client.delete_blob()

    def stream_blob(self, blob_name: str):
        """
        Stream a blob from Azure Blob Storage.
        Returns a StorageStreamDownloader object.
        """
        log.debug(f"Streaming blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        return blob_client.download_blob()
