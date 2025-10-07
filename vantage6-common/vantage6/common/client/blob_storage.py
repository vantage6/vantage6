import uuid
import requests

from vantage6.common.globals import (
    REQUEST_TIMEOUT,
    DEFAULT_CHUNK_SIZE,
)
from vantage6.common.client.utils import is_uuid


class BlobStorageMixin:
    """
    Mixin class to add blob storage functionality to client classes.
    """

    def _upload_run_data_to_server(
        self, run_data_bytes: bytes, pub_key: str | None = None
    ) -> str:
        """
        Upload run data (result or input) to the server in chunks.

        Parameters
        ----------
        run_data_bytes : bytes
            The run data to upload (result or input) as bytes.
        pub_key : str | None, optional
            Public key of the organization uploading the data. This is only required when
            streaming data from the algorithm container, since data is then streamed through
            the node proxy, and encryption takes place there chunk by chunk.

        Returns
        -------
        str | None
            UUID of the uploaded run data, or None if upload failed.
        """
        headers = self.headers
        headers["Content-Type"] = "application/octet-stream"
        if pub_key:
            headers["X-Public-Key"] = pub_key
        url = self.generate_path_to("blobstream", False)

        def chunked_run_data_stream(
            run_data: bytes, chunk_size: int = DEFAULT_CHUNK_SIZE
        ):
            for i in range(0, len(run_data), chunk_size):
                yield run_data[i : i + chunk_size]

        try:
            response = requests.post(
                url, data=chunked_run_data_stream(run_data_bytes), headers=headers
            )
        except requests.RequestException as e:
            self.log.error(f"Error occurred while uploading blob stream: {e}")
            raise requests.RequestException(
                "Error occurred while uploading blob stream"
            )

        if not (200 <= response.status_code < 300):
            error_msg = f"Failed to upload blob to server: {response.text}"
            self.log.error(error_msg)
            raise RuntimeError(error_msg)

        run_data_uuid_response = response.json()
        run_data_uuid = run_data_uuid_response.get("uuid")
        if not run_data_uuid:
            self.log.error("Failed to upload run data to server")
            raise RuntimeError("Failed to get UUID from blobstream response")
        self.log.info(f"Run data uploaded to server with UUID: {run_data_uuid}")
        return run_data_uuid

    def _download_run_data_from_server(self, run_data_uuid: str) -> bytes:
        """
        Download run data (either input or result)
        from the server using its UUID.

        Parameters
        ----------
        run_data_uuid : str
            UUID of the run data to download.

        Returns
        -------
        bytes
            The downloaded run data as bytes.

        Raises
        ------
        ValueError
            If the provided UUID is not valid.
        requests.RequestException
            If there is an error during the request to download the run data.

        """
        if not is_uuid(run_data_uuid):
            error_msg = f"Input is not a valid UUID: {run_data_uuid}"
            self.log.error(error_msg)
            raise ValueError(error_msg)
        uuid_obj = uuid.UUID(run_data_uuid)
        self.log.debug(f"Downloading run data with UUID: {uuid_obj}")
        base_path = self.generate_path_to("blobstream", False)
        url = f"{base_path}/{str(uuid_obj)}"
        headers = self.headers
        headers["Content-Type"] = "application/octet-stream"
        self.log.debug(f"Streaming run data from {url}")
        run_data = b""
        try:
            with requests.get(
                url, headers=headers, stream=True, timeout=REQUEST_TIMEOUT
            ) as response:
                if response.status_code == 200:
                    self.log.debug("Successfully requested run data stream.")
                    for chunk in response.iter_content(chunk_size=DEFAULT_CHUNK_SIZE):
                        run_data += chunk
                else:
                    self.log.error(
                        f"Failed to stream run data for uuid {run_data_uuid}. Status code: {response.status_code}"
                    )
                    self.log.error(f"Response: {response.text}")
                    raise requests.RequestException(
                        f"Failed to stream run data for uuid {run_data_uuid}. Status code: {response.status_code}"
                    )
        except requests.RequestException as e:
            self.log.error(
                f"An error occurred while streaming run data for uuid {run_data_uuid}: {e}"
            )
            raise requests.RequestException(
                f"An error occurred while streaming run data for uuid {run_data_uuid}",
                e,
            )
        return run_data

    def check_if_blob_store_enabled(self):
        """
        Check if the blob store is enabled on the server.
        This function sends a request to the blob stream status endpoint
        and returns whether the blob store is enabled or not.

        This is used so that the user does not need to be aware of storage
        used at the server when uploading the first input in the client.

        Returns
        -------
        bool
            True if blob store is enabled, False otherwise.

        Raises
        ------
        requests.RequestException
            If the request to check blob store status fails.
        """
        base_url = self.generate_path_to("blobstream", False)
        status_url = f"{base_url}/status"
        headers = self.headers
        headers["Content-Type"] = "application/octet-stream"
        response = requests.get(status_url, headers=headers)
        if not response.ok:
            self.log.warning(
                f"Blob store check failed with status code {response.status_code}. "
                "Assuming blob store is disabled. Does the server version match this client's version?"
            )
            return False
        response_json = response.json()
        return response_json.get("blob_store_enabled", False)
