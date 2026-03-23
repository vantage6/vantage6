import json
import logging
import urllib.parse
from typing import Callable

import requests

from vantage6.common import logger_name


class TesClient:
    """
    Minimal GA4GH TES HTTP client.

    TES itself does not standardize authentication. If the endpoint requires
    auth, provide an ``auth_headers_fn`` callable that returns the required
    HTTP headers.
    """

    def __init__(
        self,
        *,
        base_url: str,
        auth_headers_fn: Callable[[], dict[str, str]] | None = None,
        timeout_s: int = 30,
    ) -> None:
        self.log = logging.getLogger(logger_name(__name__))
        self.base_url = base_url.rstrip("/")
        self._auth_headers_fn = auth_headers_fn
        self.timeout_s = timeout_s

    def _headers(self) -> dict[str, str]:
        return dict(self._auth_headers_fn() if self._auth_headers_fn else {})

    def create_task(self, tes_task: dict) -> str:
        url = self.base_url + "/v1/tasks"
        resp = requests.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            data=json.dumps(tes_task),
            timeout=max(self.timeout_s, 120),
        )
        if not resp.ok:
            self.log.error(
                "TES create_task failed: %s %s", resp.status_code, resp.text[:500]
            )
        resp.raise_for_status()
        data = resp.json()
        task_id = data.get("id") or data.get("Id")
        if not task_id:
            raise RuntimeError(f"Unexpected create task response: {data!r}")
        return str(task_id)

    def get_task(self, task_id: str, *, view: str = "FULL") -> dict:
        url = (
            self.base_url
            + f"/v1/tasks/{urllib.parse.quote(str(task_id))}?"
            + urllib.parse.urlencode({"view": view})
        )
        resp = requests.get(url, headers=self._headers(), timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected get task response: {data!r}")
        return data

    def cancel_task(self, task_id: str) -> None:
        url = self.base_url + f"/v1/tasks/{urllib.parse.quote(str(task_id))}:cancel"
        resp = requests.post(url, headers=self._headers(), timeout=self.timeout_s)
        resp.raise_for_status()
