from azure.storage.blob import BlobServiceClient
from azure.identity import ClientSecretCredential
import logging
from vantage6.common import logger_name

module_name = logger_name(__name__)
log = logging.getLogger(module_name)

class AzureStorageService:
    def __init__(self, tenant_id: str, client_id: str, client_secret: str, storage_account_name: str, container_name: str):
        credential = ClientSecretCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            client_secret=client_secret,
        )
        self.blob_service_client = BlobServiceClient(
            account_url=f"https://{storage_account_name}.blob.core.windows.net/",
            credential=credential,
        )
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

    def stream_blob(self, blob_name: str) -> bytes:
        """
        Stream a blob from Azure Blob Storage.
        """
        log.debug(f"Streaming blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(container=self.container_name, blob=blob_name)
        return blob_client.download_blob()
