import logging
import time
import urllib.parse
from dataclasses import dataclass

import requests

from vantage6.common import logger_name
from vantage6.node.tes_relay.tes_client import TesClient


@dataclass(frozen=True)
class KeycloakPasswordGrant:
    token_url: str
    client_id: str
    client_secret: str
    username: str
    password: str


class DareSubmissionLayerClient:
    """
    DARE-specific client that authenticates via Keycloak password-grant, uses
    DARE's ProjectController endpoints to resolve submission buckets and upload
    files, and exposes a :class:`TesClient` for ``/v1/tasks`` calls.
    """

    def __init__(
        self,
        *,
        submission_api_base: str,
        keycloak: KeycloakPasswordGrant,
        timeout_s: int = 30,
    ) -> None:
        self.log = logging.getLogger(logger_name(__name__))
        self.submission_api_base = submission_api_base.rstrip("/")
        self.keycloak = keycloak
        self.timeout_s = timeout_s

        self._cached_token: str | None = None
        self._cached_token_expires_at: float = 0.0

        self.tes = TesClient(
            base_url=self.submission_api_base,
            auth_headers_fn=self._authz_headers,
            timeout_s=timeout_s,
        )

    @classmethod
    def from_tes_relay_config(
        cls,
        *,
        tes_endpoint: str,
        tes_relay_cfg: dict,
    ) -> "DareSubmissionLayerClient":
        kc_cfg = tes_relay_cfg.get("keycloak")
        if not isinstance(kc_cfg, dict):
            raise RuntimeError("tes_relay.keycloak is required and must be a mapping")
        keycloak = KeycloakPasswordGrant(
            token_url=str(kc_cfg.get("token_url") or ""),
            client_id=str(kc_cfg.get("client_id") or ""),
            client_secret=str(kc_cfg.get("client_secret") or ""),
            username=str(kc_cfg.get("username") or ""),
            password=str(kc_cfg.get("password") or ""),
        )
        missing = [k for k, v in keycloak.__dict__.items() if not v]
        if missing:
            raise RuntimeError(
                "tes_relay enabled but keycloak config is missing: "
                + ", ".join(missing)
            )
        return cls(
            submission_api_base=str(tes_endpoint),
            keycloak=keycloak,
            timeout_s=int(tes_relay_cfg.get("timeout_s", 30)),
        )

    def _get_token(self) -> str:
        now = time.time()
        if self._cached_token and now < (self._cached_token_expires_at - 10):
            return self._cached_token

        form = {
            "grant_type": "password",
            "client_id": self.keycloak.client_id,
            "client_secret": self.keycloak.client_secret,
            "username": self.keycloak.username,
            "password": self.keycloak.password,
        }
        resp = requests.post(self.keycloak.token_url, data=form, timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token")
        if not token:
            raise RuntimeError(f"Unexpected token response: {data!r}")
        expires_in = float(data.get("expires_in") or 60)
        self._cached_token = str(token)
        self._cached_token_expires_at = now + expires_in
        return self._cached_token

    def _authz_headers(self) -> dict[str, str]:
        token = self._get_token()
        return {"Authorization": f"Bearer {token}"}

    def get_project(self, project_id: int) -> dict:
        url = (
            self.submission_api_base
            + "/api/Project/GetProject?"
            + urllib.parse.urlencode({"projectId": str(project_id)})
        )
        resp = requests.get(url, headers=self._authz_headers(), timeout=self.timeout_s)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict):
            raise RuntimeError(f"Unexpected project response: {data!r}")
        return data

    @staticmethod
    def project_bucket(project: dict, key: str) -> str:
        v = project.get(key) or project.get(key[:1].upper() + key[1:])
        if not v:
            raise RuntimeError(f"Project JSON missing {key}: {project!r}")
        return str(v)

    def upload_to_minio(
        self, *, bucket_name: str, object_name: str, content_bytes: bytes
    ) -> None:
        url = (
            self.submission_api_base
            + "/api/Project/UploadToMinio?"
            + urllib.parse.urlencode({"bucketName": bucket_name})
        )
        files = {
            "file": (object_name, content_bytes, "application/octet-stream"),
        }
        resp = requests.post(
            url,
            headers=self._authz_headers(),
            files=files,
            timeout=max(self.timeout_s, 120),
        )
        resp.raise_for_status()

    def get_submission_status(self, tes_id: str) -> int | None:
        url = self.submission_api_base + "/api/Submission/GetAllSubmissions"
        resp = requests.get(url, headers=self._authz_headers(), timeout=self.timeout_s)
        resp.raise_for_status()
        items = resp.json()
        ref_map: dict[str, dict] = {}
        self._index_refs(items, ref_map)
        all_subs = []
        for item in items:
            if "$ref" in item:
                resolved = ref_map.get(item["$ref"])
                if resolved:
                    all_subs.append(resolved)
            else:
                all_subs.append(item)
        for sub in all_subs:
            sub_tes = sub.get("tesId")
            if str(sub_tes) != str(tes_id):
                continue
            parent = sub.get("parentId")
            if parent is None:
                parent = sub.get("parentID")
            if parent is not None:
                continue
            status = sub.get("status")
            return int(status) if status is not None else None
        return None

    @staticmethod
    def _index_refs(obj, ref_map: dict) -> None:
        if isinstance(obj, dict):
            if "$id" in obj:
                ref_map[obj["$id"]] = obj
            for v in obj.values():
                DareSubmissionLayerClient._index_refs(v, ref_map)
        elif isinstance(obj, list):
            for v in obj:
                DareSubmissionLayerClient._index_refs(v, ref_map)

    def resolve_submission_bucket(self, *, dare_cfg: dict) -> str:
        bucket = dare_cfg.get("submission_bucket")
        if bucket:
            return str(bucket)

        project_id = dare_cfg.get("project_id")
        if project_id is None:
            raise RuntimeError(
                "tes_relay.dare requires either dare.submission_bucket or dare.project_id"
            )

        project = self.get_project(int(project_id))
        return self.project_bucket(project, "submissionBucket")
