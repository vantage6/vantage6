from azure.storage.blob import BlobServiceClient
import logging
from vantage6.common import logger_name
from typing import IO, Union
from sqlalchemy import event
from vantage6.server.model.run import Run

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class AzureStorageService:
    """
    A service for managing Azure Blob Storage.
    """

    def __init__(
        self,
        container_name: str,
        blob_service_client: BlobServiceClient
    ):
        """
        Initialize the AzureStorageService.

        Parameters
        ----------
        container_name : str
            The name of the storage container in azure in which the blobs are 
            stored. Containers in azure are stored on three levels:
            1. Storage Account
            2. Container
            3. Blob 
        blob_service_client : BlobServiceClient
            An existing BlobServiceClient instance. Defaults to None.
        """

        if container_name:
            self.container_name = container_name
        else:
            raise ValueError("Container name must be provided.")

        if blob_service_client:
            self.blob_service_client = blob_service_client
        else:
            raise ValueError(
                "Either 'connection_string' or 'blob_service_client' must be provided."
            )

        self.container_client = self.blob_service_client.get_container_client(
            container_name
        )
        event.listen(Run, 'after_delete', self.delete_blob_after_run_delete)


    def get_blob(self, blob_name: str) -> bytes:
        """
        Retrieve a blob from Azure Blob Storage by its name.

        Parameters
        ----------
        blob_name : str
            The name of the blob to retrieve.

        Returns
        -------
        bytes
            The content of the blob.
        """
        log.debug(f"Retrieving blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )
        stream = blob_client.download_blob()
        return stream.readall()

    def store_blob(self, blob_name: str, data: Union[IO, bytes]) -> None:
        """
        Store data as a blob in Azure Blob Storage.

        Parameters
        ----------
        blob_name : str
            The name of the blob to create or overwrite.
        data : Union[IO, bytes]
            The data to store in the blob. Can be a bytes object or a file-like
            object.
        """
        log.debug(f"Storing blob: {blob_name} in container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )
        try:
            blob_client.upload_blob(data, overwrite=True)
        except Exception as e:
            log.error(f"Failed to upload blob '{blob_name}': {e}")
            raise RuntimeError(f"Failed to upload blob '{blob_name}': {e}")

    def delete_blob(self, blob_name: str) -> None:
        """
        Delete a blob from Azure Blob Storage by its name.

        Parameters
        ----------
        blob_name : str
            The name of the blob to delete.
        """
        log.debug(f"Deleting blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )
        blob_client.delete_blob()

    def stream_blob(self, blob_name: str):
        """
        Stream a blob from Azure Blob Storage.
        Returns a StorageStreamDownloader object.

        Parameters
        ----------
        blob_name : str
            The name of the blob to stream.

        Returns
        -------
        StorageStreamDownloader
            A stream object to read the blob's content in chunks.
        """
        log.debug(f"Streaming blob: {blob_name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=blob_name
        )
        return blob_client.download_blob()

    def delete_blob_after_run_delete(self, mapper, connection, target):
        """
        SQLAlchemy event listener to delete the associated blob when a Run
        instance is deleted.
        """
        if target.blob_storage_used:
            try:
                self.delete_blob(target.result)
            except Exception as e:
                error_msg = f"Failed to delete blob for run {target.id}: {e}"
                log.error(error_msg)
                connection.rollback()
                raise RuntimeError(error_msg)
