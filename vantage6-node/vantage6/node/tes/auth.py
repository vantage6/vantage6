import time
import logging

import requests

from vantage6.common import logger_name


class KeycloakAuth:
    def __init__(self, keycloak_config: dict):
        self.log = logging.getLogger(logger_name(__name__))
        self._token_url = keycloak_config["token_url"]
        self._client_id = keycloak_config["client_id"]
        self._client_secret = keycloak_config["client_secret"]
        self._audience = keycloak_config.get("audience", "")
        self._access_token: str | None = None
        self._expires_at: float = 0

    def get_token(self) -> str:
        if self._access_token and time.time() < (self._expires_at - 30):
            return self._access_token
        self._refresh_token()
        return self._access_token

    def _refresh_token(self) -> None:
        self.log.debug("Requesting new Keycloak token from %s", self._token_url)
        data = {
            "grant_type": "client_credentials",
            "client_id": self._client_id,
            "client_secret": self._client_secret,
        }
        if self._audience:
            data["audience"] = self._audience

        response = requests.post(self._token_url, data=data, timeout=30)
        response.raise_for_status()

        token_data = response.json()
        self._access_token = token_data["access_token"]
        self._expires_at = time.time() + token_data.get("expires_in", 300)
        self.log.debug(
            "Keycloak token obtained, expires in %ss",
            token_data.get("expires_in"),
        )
