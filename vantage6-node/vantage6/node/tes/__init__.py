import logging

from vantage6.common import logger_name
from vantage6.node.tes.auth import KeycloakAuth
from vantage6.node.tes.client import TesClient
from vantage6.node.tes.converter import convert_task_to_tes


class TesForwarder:
    def __init__(self, config: dict):
        self.log = logging.getLogger(logger_name(__name__))
        tes_config = config["tes_forwarding"]
        self._auth = KeycloakAuth(tes_config["keycloak"])
        self._client = TesClient(
            endpoint=tes_config["endpoint"],
            auth=self._auth,
        )
        self._default_resources = tes_config.get("resources", {})

    def forward_task(self, task_incl_run: dict) -> str:
        tes_body = convert_task_to_tes(task_incl_run, self._default_resources)
        tes_task_id = self._client.create_task(tes_body)
        self.log.info(
            "Forwarded run_id=%s to TES, received TES task id=%s",
            task_incl_run["id"],
            tes_task_id,
        )
        return tes_task_id
