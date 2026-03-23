#!/usr/bin/env python3
"""
Auto-approve pending DARE Data-Egress requests.

Standalone script (no vantage6 dependencies, only ``requests``). Designed for
automated testing against the 5S-TES / TREvolution demo stack where egress
approval is required before task outputs are released.

Usage::

    uv run python scripts/dare_egress_approve.py
    uv run python scripts/dare_egress_approve.py --interval 3 --username myuser
"""

import argparse
import logging
import os
import sys
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("dare-egress-approve")


def get_token(
    keycloak_url: str,
    realm: str,
    client_id: str,
    client_secret: str,
    username: str,
    password: str,
) -> str:
    token_url = (
        f"{keycloak_url.rstrip('/')}/realms/{realm}" f"/protocol/openid-connect/token"
    )
    resp = requests.post(
        token_url,
        data={
            "grant_type": "password",
            "client_id": client_id,
            "client_secret": client_secret,
            "username": username,
            "password": password,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


def poll_and_approve(
    egress_api: str,
    token: str,
) -> int:
    headers = {"Authorization": f"Bearer {token}"}

    resp = requests.get(
        f"{egress_api.rstrip('/')}/api/DataEgress/GetAllEgresses",
        params={"unprocessedonly": "true"},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    egresses = resp.json()

    if not egresses:
        return 0

    approved = 0
    for egress in egresses:
        status = egress.get("status")
        if status is None:
            status = egress.get("Status")
        if status not in (0, None, "NotCompleted"):
            continue

        egress_id = (
            egress.get("id") if egress.get("id") is not None else egress.get("Id")
        )
        log.info("Processing egress id=%s", egress_id)

        files = egress.get("files") or egress.get("Files") or []
        approved_files = []
        for f in files:
            file_id = f.get("id") if f.get("id") is not None else f.get("Id")
            if file_id is None:
                continue
            file_status = f.get("status")
            if file_status is None:
                file_status = f.get("Status")
            if file_status != 1:
                resp = requests.post(
                    f"{egress_api.rstrip('/')}/api/DataEgress/UpdateFileData",
                    params={"fileId": str(file_id), "status": "1"},
                    headers=headers,
                    timeout=30,
                )
                resp.raise_for_status()
                log.info("  Approved file id=%s", file_id)
            approved_files.append(
                {
                    "id": file_id,
                    "name": f.get("name") or f.get("Name") or "",
                    "status": 1,
                }
            )

        complete_body = {
            "id": egress_id,
            "submissionId": egress.get("submissionId") or egress.get("SubmissionId"),
            "status": 1,
            "outputBucket": egress.get("outputBucket") or egress.get("OutputBucket"),
            "files": approved_files,
        }
        resp = requests.post(
            f"{egress_api.rstrip('/')}/api/DataEgress/CompleteEgress",
            json=complete_body,
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        log.info("  Completed egress id=%s", egress_id)
        approved += 1

    return approved


def main():
    parser = argparse.ArgumentParser(
        description="Auto-approve DARE Data-Egress requests"
    )
    parser.add_argument(
        "--egress-api",
        default=os.environ.get("EGRESS_API", "http://localhost:8101"),
    )
    parser.add_argument(
        "--keycloak-url",
        default=os.environ.get("KEYCLOAK_URL", "http://localhost:8085"),
    )
    parser.add_argument(
        "--realm",
        default=os.environ.get("EGRESS_REALM", "Data-Egress"),
    )
    parser.add_argument(
        "--client-id",
        default=os.environ.get("EGRESS_CLIENT_ID", "Data-Egress-API"),
    )
    parser.add_argument(
        "--client-secret",
        default=os.environ.get("EGRESS_CLIENT_SECRET", ""),
    )
    parser.add_argument(
        "--username",
        default=os.environ.get("EGRESS_USERNAME", ""),
    )
    parser.add_argument(
        "--password",
        default=os.environ.get("EGRESS_PASSWORD", ""),
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("EGRESS_INTERVAL", "5")),
    )
    args = parser.parse_args()

    log.info(
        "Starting egress auto-approver: api=%s keycloak=%s realm=%s interval=%ds",
        args.egress_api,
        args.keycloak_url,
        args.realm,
        args.interval,
    )

    token = None
    token_obtained_at = 0.0
    token_lifetime = 250

    while True:
        try:
            now = time.time()
            if token is None or (now - token_obtained_at) > token_lifetime:
                log.info("Obtaining Keycloak token...")
                token = get_token(
                    keycloak_url=args.keycloak_url,
                    realm=args.realm,
                    client_id=args.client_id,
                    client_secret=args.client_secret,
                    username=args.username,
                    password=args.password,
                )
                token_obtained_at = now
                log.info("Token obtained successfully")

            n = poll_and_approve(args.egress_api, token)
            if n:
                log.info("Approved %d egress request(s)", n)
        except KeyboardInterrupt:
            log.info("Interrupted, exiting.")
            sys.exit(0)
        except Exception:
            log.exception("Error during poll cycle")
            token = None

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
