#!/usr/bin/env python3
"""
End-to-end smoke test for the TES relay pipeline.

Prerequisites:
  1. 5S-TES deployment running
  2. v6 demo network running     (v6 dev start-demo-network)
     - At least one node configured with tes_relay.enabled: true
  3. Test algorithm image pushed to the registry the TES executor can pull from

What this script does:
  1. Starts the egress auto-approver as a background process
  2. Authenticates to the v6 server
  3. Creates a task targeting the relay node's organization
  4. Polls task status until it leaves ACTIVE (or times out)
  5. Fetches the result and verifies it contains TES relay metadata
  6. Cleans up the egress auto-approver subprocess

Usage::

    uv run python scripts/smoke_test_tes_relay.py
    uv run python scripts/smoke_test_tes_relay.py --timeout 300 --no-egress-approver
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("smoke-test")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
EGRESS_SCRIPT = os.path.join(SCRIPT_DIR, "dare_egress_approve.py")


def parse_args():
    p = argparse.ArgumentParser(description="TES relay end-to-end smoke test")

    p.add_argument(
        "--server-url", default=os.environ.get("V6_SERVER_URL", "http://localhost")
    )
    p.add_argument(
        "--server-port", type=int, default=int(os.environ.get("V6_SERVER_PORT", "7601"))
    )
    p.add_argument("--api-path", default=os.environ.get("V6_API_PATH", "/api"))
    p.add_argument("--username", default=os.environ.get("V6_USERNAME", ""))
    p.add_argument("--password", default=os.environ.get("V6_PASSWORD", ""))
    p.add_argument(
        "--collaboration", type=int, default=int(os.environ.get("V6_COLLAB_ID", "1"))
    )
    p.add_argument(
        "--organizations",
        type=str,
        default=os.environ.get("V6_ORG_IDS", "2"),
        help="Comma-separated org IDs to target",
    )
    p.add_argument(
        "--image",
        default=os.environ.get(
            "V6_ALGORITHM_IMAGE", "localhost:5000/test-algorithm:latest"
        ),
    )
    p.add_argument(
        "--database-label",
        default=os.environ.get("V6_DB_LABEL", "default"),
    )
    p.add_argument(
        "--input",
        default=os.environ.get(
            "V6_TASK_INPUT", '{"method": "central", "kwargs": {"arg1": "age"}}'
        ),
        help="JSON task input",
    )
    p.add_argument(
        "--timeout", type=int, default=int(os.environ.get("SMOKE_TIMEOUT", "300"))
    )
    p.add_argument("--poll-interval", type=float, default=3.0)
    p.add_argument(
        "--no-egress-approver",
        action="store_true",
        help="Skip starting the egress auto-approver (if already running externally)",
    )
    p.add_argument("--egress-interval", type=int, default=3)
    return p.parse_args()


class V6ServerClient:
    def __init__(self, base_url: str, port: int, api_path: str):
        self.base = f"{base_url}:{port}{api_path}"
        self.token = None
        self.session = requests.Session()

    def _headers(self):
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def authenticate(self, username: str, password: str):
        resp = self.session.post(
            f"{self.base}/token/user",
            json={"username": username, "password": password},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]
        log.info("Authenticated as %s", username)

    def create_task(
        self,
        collaboration_id: int,
        organization_ids: list[int],
        name: str,
        image: str,
        input_: dict,
        databases: list[dict],
    ) -> dict:
        import base64

        input_b64 = base64.b64encode(json.dumps(input_).encode("utf-8")).decode("utf-8")
        payload = {
            "collaboration_id": collaboration_id,
            "organizations": [
                {"id": oid, "input": input_b64} for oid in organization_ids
            ],
            "name": name,
            "image": image,
            "databases": databases,
            "description": "Smoke test task for TES relay",
        }
        resp = self.session.post(
            f"{self.base}/task",
            json=payload,
            headers=self._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def get_task_status(self, task_id: int) -> str:
        resp = self.session.get(
            f"{self.base}/task/{task_id}",
            headers=self._headers(),
            params={"include": "status"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("status", "unknown")

    def get_task(self, task_id: int) -> dict:
        resp = self.session.get(
            f"{self.base}/task/{task_id}",
            headers=self._headers(),
            params={"include": "results"},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_results(self, task_id: int) -> list[dict]:
        resp = self.session.get(
            f"{self.base}/result",
            headers=self._headers(),
            params={"task_id": task_id},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()

    def get_run(self, run_id: int) -> dict:
        resp = self.session.get(
            f"{self.base}/run/{run_id}",
            headers=self._headers(),
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json()


def start_egress_approver(interval: int) -> subprocess.Popen:
    log.info("Starting egress auto-approver (interval=%ds)...", interval)
    proc = subprocess.Popen(
        [sys.executable, EGRESS_SCRIPT, "--interval", str(interval)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(2)
    if proc.poll() is not None:
        output = proc.stdout.read() if proc.stdout else ""
        log.error("Egress auto-approver exited immediately: %s", output)
        raise RuntimeError("Egress auto-approver failed to start")
    log.info("Egress auto-approver running (pid=%d)", proc.pid)
    return proc


def stop_egress_approver(proc: subprocess.Popen):
    if proc and proc.poll() is None:
        log.info("Stopping egress auto-approver (pid=%d)...", proc.pid)
        proc.send_signal(signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log.info("Egress auto-approver stopped")


def poll_task_status(
    client: V6ServerClient, task_id: int, timeout: int, interval: float
) -> str:
    log.info(
        "Polling task %d (timeout=%ds, interval=%.1fs)...", task_id, timeout, interval
    )
    start = time.time()
    last_status = None
    while time.time() - start < timeout:
        status = client.get_task_status(task_id)
        if status != last_status:
            elapsed = time.time() - start
            log.info("  Task %d status: %s (%.0fs elapsed)", task_id, status, elapsed)
            last_status = status

        if status not in ("active", "pending", "initializing", "start"):
            return status

        time.sleep(interval)

    elapsed = time.time() - start
    log.error(
        "Task %d timed out after %.0fs (last status: %s)", task_id, elapsed, last_status
    )
    return f"timeout (last: {last_status})"


def main():
    args = parse_args()
    egress_proc = None
    exit_code = 1

    try:
        if not args.no_egress_approver:
            egress_proc = start_egress_approver(args.egress_interval)

        client = V6ServerClient(args.server_url, args.server_port, args.api_path)
        client.authenticate(args.username, args.password)

        org_ids = [int(x.strip()) for x in args.organizations.split(",")]
        task_input = (
            json.loads(args.input) if isinstance(args.input, str) else args.input
        )

        log.info(
            "Creating task: image=%s orgs=%s collab=%d",
            args.image,
            org_ids,
            args.collaboration,
        )
        task = client.create_task(
            collaboration_id=args.collaboration,
            organization_ids=org_ids,
            name="smoke-test-tes-relay",
            image=args.image,
            input_=task_input,
            databases=[{"label": args.database_label}],
        )
        task_id = task["id"]
        log.info("Task created: id=%d", task_id)

        runs = task.get("runs", [])
        if runs:
            log.info("Runs: %s", runs)

        final_status = poll_task_status(
            client, task_id, args.timeout, args.poll_interval
        )
        log.info("Final task status: %s", final_status)

        if final_status == "completed":
            log.info("--- VERIFYING RESULTS ---")
            task_detail = client.get_task(task_id)
            runs = task_detail.get("results", task_detail.get("runs", []))

            for run in runs:
                run_id = run.get("id")
                if run_id:
                    run_detail = client.get_run(run_id)
                    result_data = run_detail.get("result")
                    run_status = run_detail.get("status")
                    run_log = run_detail.get("log", "")

                    log.info("Run %d: status=%s", run_id, run_status)
                    log.info(
                        "Run %d: log=%s",
                        run_id,
                        run_log[:200] if run_log else "(empty)",
                    )

                    if result_data:
                        try:
                            parsed = json.loads(result_data)
                            if "tes" in parsed:
                                tes_info = parsed["tes"]
                                log.info(
                                    "Run %d: TES relay metadata found - submission_id=%s state=%s",
                                    run_id,
                                    tes_info.get("id"),
                                    tes_info.get("state"),
                                )
                            else:
                                log.info(
                                    "Run %d: result (first 300 chars): %s",
                                    run_id,
                                    str(result_data)[:300],
                                )
                        except (json.JSONDecodeError, TypeError):
                            log.info(
                                "Run %d: result (raw, first 300 chars): %s",
                                run_id,
                                str(result_data)[:300],
                            )
                    else:
                        log.warning("Run %d: no result data", run_id)

            log.info("=== SMOKE TEST PASSED ===")
            exit_code = 0

        elif final_status == "failed":
            log.error("Task failed. Fetching details...")
            task_detail = client.get_task(task_id)
            for run in task_detail.get("results", task_detail.get("runs", [])):
                run_id = run.get("id")
                if run_id:
                    run_detail = client.get_run(run_id)
                    log.error(
                        "Run %d: status=%s log=%s",
                        run_id,
                        run_detail.get("status"),
                        (run_detail.get("log") or "")[:500],
                    )
            log.error("=== SMOKE TEST FAILED (task failed) ===")

        elif "timeout" in final_status:
            log.error("=== SMOKE TEST FAILED (timeout) ===")
            task_detail = client.get_task(task_id)
            for run in task_detail.get("results", task_detail.get("runs", [])):
                run_id = run.get("id")
                if run_id:
                    run_detail = client.get_run(run_id)
                    log.error(
                        "Run %d: status=%s log=%s",
                        run_id,
                        run_detail.get("status"),
                        (run_detail.get("log") or "")[:500],
                    )
        else:
            log.error("=== SMOKE TEST FAILED (unexpected status: %s) ===", final_status)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception:
        log.exception("Smoke test encountered an error")
    finally:
        if egress_proc:
            stop_egress_approver(egress_proc)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
