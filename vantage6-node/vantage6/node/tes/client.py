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
        url = f"{self._endpoint}/tasks"
        self.log.debug("POSTing TES task to %s", url)
        response = requests.post(
            url, json=tes_body, headers=self._headers(), timeout=60
        )
        response.raise_for_status()
        result = response.json()
        return result["id"]
