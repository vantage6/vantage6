import logging

import requests

from vantage6.common import logger_name
from vantage6.node.tes.auth import KeycloakAuth


class TesClient:
    def __init__(self, endpoint: str, auth: KeycloakAuth):
        self.log = logging.getLogger(logger_name(__name__))
        self._endpoint = endpoint.rstrip("/")
        self._auth = auth

    def _headers(self) -> dict:
        token = self._auth.get_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def create_task(self, tes_body: dict) -> str:
        url = f"{self._endpoint}/v1/tasks"
        self.log.debug("POSTing TES task to %s", url)
        response = requests.post(
            url, json=tes_body, headers=self._headers(), timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return result["id"]

    def upload_input(self, bucket: str, name: str, data: bytes) -> None:
        url = f"{self._endpoint}/api/Project/UploadToMinio"
        self.log.debug("Uploading input %s to bucket %s via %s", name, bucket, url)
        token = self._auth.get_token()
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.post(
            url,
            params={"bucketName": bucket},
            files={"file": (name, data)},
            headers=headers,
            timeout=120,
        )
        response.raise_for_status()
