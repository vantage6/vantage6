import json
import logging

from vantage6.common import logger_name
from vantage6.node.tes.auth import KeycloakAuth
from vantage6.node.tes.client import TesClient
from vantage6.node.tes.converter import convert_task_to_tes

MAX_INLINE_SIZE = 128 * 1024


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
        self._project = tes_config["project"]
        self._tres = tes_config.get("tres")
        minio_config = tes_config.get("minio", {})
        self._bucket = minio_config.get("bucket")

    def forward_task(self, task_incl_run: dict) -> str:
        input_url = self._maybe_upload_input(task_incl_run)
        tes_body = convert_task_to_tes(
            task_incl_run,
            self._default_resources,
            project=self._project,
            tres=self._tres,
            input_url=input_url,
        )
        tes_task_id = self._client.create_task(tes_body)
        self.log.info(
            "Forwarded run_id=%s to TES, received TES task id=%s",
            task_incl_run["id"],
            tes_task_id,
        )
        return tes_task_id

    def _maybe_upload_input(self, task_incl_run: dict) -> str | None:
        input_data = task_incl_run.get("input", "")
        if isinstance(input_data, dict):
            raw = json.dumps(input_data).encode("utf-8")
        elif isinstance(input_data, str):
            raw = input_data.encode("utf-8")
        elif isinstance(input_data, bytes):
            raw = input_data
        else:
            return None

        if len(raw) <= MAX_INLINE_SIZE:
            return None

        if not self._bucket:
            self.log.warning(
                "Input exceeds 128 KiB but no minio bucket configured, "
                "sending inline anyway"
            )
            return None

        run_id = task_incl_run["id"]
        name = f"v6-run-{run_id}-input.bin"
        self._client.upload_input(self._bucket, name, raw)
        input_url = f"s3://{self._bucket}/{name}"
        self.log.info(
            "Uploaded input for run_id=%s to %s (%d bytes)",
            run_id,
            input_url,
            len(raw),
        )
        return input_url
