"""Azure Blob Storage backend for the large result store."""

import logging
from typing import IO, Union

from azure.core.exceptions import ResourceNotFoundError
from azure.identity import ClientSecretCredential
from azure.storage.blob import BlobServiceClient

from vantage6.common import logger_name
from vantage6.server.service.storage_adapter import (
    RunDataNotFoundError,
    StorageAdapter,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


class AzureStorageService(StorageAdapter):
    """
    A service for managing Azure Blob Storage.
    """

    def __init__(self, config: dict):
        """
        Initialize the AzureStorageService.

        Parameters
        ----------
        config : dict
            Configuration dictionary containing Azure Blob Storage settings.
        """
        self.blob_service_client = None

        tenant_id = config.get("tenant_id")
        client_id = config.get("client_id")
        client_secret = config.get("client_secret")
        storage_account_name = config.get("storage_account_name")
        container_name = config.get("container_name")
        connection_string = config.get("connection_string")

        if tenant_id and client_id and client_secret and storage_account_name:
            credential = ClientSecretCredential(
                tenant_id=tenant_id, client_id=client_id, client_secret=client_secret
            )
            self.blob_service_client = BlobServiceClient(
                account_url=f"https://{storage_account_name}.blob.core.windows.net/",
                credential=credential,
            )

        if connection_string:
            self.blob_service_client = BlobServiceClient.from_connection_string(
                connection_string
            )

        if not self.blob_service_client:
            log.warning(
                "Azure Blob Storage configuration is incomplete. Large result store not set up."
            )
            return

        if container_name:
            self.container_name = container_name
        else:
            raise ValueError("Container name must be provided.")

        self.container_client = self.blob_service_client.get_container_client(
            container_name
        )
        super().__init__(config)

    def get_run_data(self, name: str) -> bytes:
        """
        Retrieve a run-data entry from Azure Blob Storage by its name.

        Parameters
        ----------
        name : str
            The name of the run-data entry (Azure blob) to retrieve.

        Returns
        -------
        bytes
            The content of the run-data entry.
        """
        log.debug(f"Retrieving run data: {name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=name
        )
        try:
            stream = blob_client.download_blob()
            return stream.readall()
        except ResourceNotFoundError as e:
            raise RunDataNotFoundError(f"Run data {name!r} not found") from e

    def store_run_data(self, name: str, data: Union[IO, bytes]) -> None:
        """
        Store data as a run-data entry in Azure Blob Storage.

        Parameters
        ----------
        name : str
            The name of the run-data entry (Azure blob) to create or
            overwrite.
        data : Union[IO, bytes]
            The data to store. Can be a bytes object or a file-like
            object.
        """
        log.debug(f"Storing run data: {name} in container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=name
        )
        try:
            blob_client.upload_blob(data, overwrite=True)
        except Exception as e:
            log.error(f"Failed to upload run data '{name}': {e}")
            raise RuntimeError(f"Failed to upload run data '{name}': {e}")

    def delete_run_data(self, name: str) -> None:
        """
        Delete a run-data entry from Azure Blob Storage by its name.

        Parameters
        ----------
        name : str
            The name of the run-data entry (Azure blob) to delete.
        """
        log.debug(f"Deleting run data: {name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=name
        )
        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            # StorageAdapter.delete_run_data is contractually idempotent;
            # the after_delete listener relies on this when a Run row whose
            # blob has already been deleted is removed from the DB.
            pass

    def stream_run_data(self, name: str):
        """
        Stream a run-data entry from Azure Blob Storage.
        Returns a StorageStreamDownloader object.

        Parameters
        ----------
        name : str
            The name of the run-data entry (Azure blob) to stream.

        Returns
        -------
        StorageStreamDownloader
            A stream object to read the run-data entry's content in chunks.
        """
        log.debug(f"Streaming run data: {name} from container: {self.container_name}")
        blob_client = self.blob_service_client.get_blob_client(
            container=self.container_name, blob=name
        )
        try:
            return blob_client.download_blob()
        except ResourceNotFoundError as e:
            raise RunDataNotFoundError(f"Run data {name!r} not found") from e
