"""
End-to-end test of a collaboration with one Kubernetes node and one Docker node.

See README.md for the setup. Exits with a non-zero code on any failure.
"""

import argparse
import csv
import json
import os
import secrets
import sys
import time
from pathlib import Path

from vantage6.common.enum import RunStatus, TaskStatus
from vantage6.common.globals import HQ_AUDIENCE_SCOPE, STORE_AUDIENCE_SCOPE

from vantage6.client import Client

HERE = Path(__file__).parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hq-url", required=True, help="e.g. https://hq.example/hq")
    parser.add_argument("--auth-url", required=True)
    parser.add_argument("--collaboration", type=int, help="existing collaboration")
    parser.add_argument(
        "--setup",
        action="store_true",
        help="create two organizations, a collaboration and two nodes, print the "
        "API keys and exit",
    )
    parser.add_argument(
        "--image", default="ghcr.io/vantage6/algorithm/session-basics:latest"
    )
    parser.add_argument("--database-label", default="default")
    parser.add_argument("--extract-method", default="read_csv")
    parser.add_argument("--extract-args", default="{}", help="JSON")
    parser.add_argument("--compute-method", default="global_sum")
    parser.add_argument("--compute-args", default="{}", help="JSON")
    parser.add_argument(
        "--column",
        default="value",
        help="column summed by the compute method, to check the result",
    )
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument(
        "--password-login",
        metavar="USERNAME",
        help="log in with a password (V6_PASSWORD) instead of in the browser; the "
        "public client must allow direct access grants",
    )
    return parser.parse_args()


def password_login(client: Client, username: str, password: str) -> None:
    token = client.kc_openid.token(
        grant_type="password",
        username=username,
        password=password,
        scope=f"openid {HQ_AUDIENCE_SCOPE} {STORE_AUDIENCE_SCOPE}",
    )
    client._refresh_token = token["refresh_token"]
    if not client._obtain_tokens_per_audience():
        fail("Could not get tokens for HQ")
    client._finalize_successful_authentication()


def setup(client: Client) -> None:
    orgs = [
        client.organization.create(
            name=name,
            address1="-",
            address2="-",
            zipcode="-",
            country="-",
            domain=f"{name}.example",
        )
        for name in ("mixed-k8s", "mixed-docker")
    ]
    collab = client.collaboration.create(
        name="mixed-runtime", organizations=[o["id"] for o in orgs], encrypted=False
    )
    print(f"collaboration: {collab['id']}")
    # Sessions are created by a member of the collaboration
    roles = [
        role["id"]
        for name in ("Researcher", "Collaboration Admin")
        for role in client.role.list(name=name, include_root=True)["data"]
    ]
    password = "Mixed-" + secrets.token_urlsafe(12) + "1!"
    client.user.create(
        username="mixed-researcher",
        password=password,
        organization=orgs[0]["id"],
        roles=roles,
    )
    print(f"user mixed-researcher: password {password}")
    for org, runtime in zip(orgs, ("kubernetes", "docker")):
        node = client.node.create(
            collaboration=collab["id"], organization=org["id"], name=org["name"]
        )
        print(f"{runtime} node {node['name']}: api key {node['api_key']}")


def wait_until_online(client: Client, collaboration: int, timeout: int) -> list:
    deadline = time.time() + timeout
    while time.time() < deadline:
        nodes = client.node.list(collaboration=collaboration)["data"]
        if nodes and all(n["status"] == "online" for n in nodes):
            return nodes
        time.sleep(5)
    fail(f"Not all nodes came online: {[(n['name'], n['status']) for n in nodes]}")


def wait_for_task(client: Client, task_id: int, timeout: int) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        task = client.task.get(task_id)
        if task["status"] in (TaskStatus.COMPLETED.value, TaskStatus.FAILED.value):
            return task
        time.sleep(3)
    fail(f"Task {task_id} did not finish within {timeout}s")


def check_runs(client: Client, task_id: int, expected_orgs: set[int]) -> None:
    runs = client.run.from_task(task_id)
    runs = runs["data"] if isinstance(runs, dict) else runs
    statuses = {run["organization"]["id"]: run["status"] for run in runs}
    print(f"  task {task_id} runs: {statuses}")
    if set(statuses) != expected_orgs:
        fail(f"Task {task_id} ran at {set(statuses)}, expected {expected_orgs}")
    failed = {org: s for org, s in statuses.items() if s != RunStatus.COMPLETED.value}
    if failed:
        fail(f"Task {task_id} has runs that did not complete: {failed}")


def expected_sum(column: str) -> float:
    total = 0.0
    for path in HERE.glob("*.csv"):
        with path.open() as f:
            total += sum(float(row[column]) for row in csv.DictReader(f))
    return total


def contains_number(value, number: float) -> bool:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return abs(value - number) < 1e-6
    if isinstance(value, dict):
        return any(contains_number(v, number) for v in value.values())
    if isinstance(value, list):
        return any(contains_number(v, number) for v in value)
    if isinstance(value, str):
        try:
            return contains_number(json.loads(value), number)
        except ValueError:
            return False
    return False


def fail(message: str) -> None:
    print(f"FAILED: {message}")
    sys.exit(1)


def main() -> None:
    args = parse_args()
    client = Client(hq_url=args.hq_url, auth_url=args.auth_url)
    if args.password_login:
        password_login(client, args.password_login, os.environ["V6_PASSWORD"])
    else:
        client.authenticate()

    if args.setup:
        setup(client)
        return
    if not args.collaboration:
        fail("--collaboration is required (create one with --setup)")

    nodes = wait_until_online(client, args.collaboration, args.timeout)
    orgs = {n["organization"]["id"] for n in nodes}
    print(f"nodes online: {[n['name'] for n in nodes]}")

    session = client.session.create(
        collaboration=args.collaboration,
        name=f"mixed-runtime {int(time.time())}",
        scope="collaboration",
    )
    print(f"session {session['id']}")

    dataframe = client.dataframe.create(
        label=args.database_label,
        image=args.image,
        method=args.extract_method,
        arguments=json.loads(args.extract_args),
        session=session["id"],
        # Dataframe names are unique across the collaboration
        name=f"data_{session['id']}",
    )
    extraction = wait_for_task(
        client, dataframe["last_session_task"]["id"], args.timeout
    )
    check_runs(client, extraction["id"], orgs)
    print("data extraction completed on both nodes")

    task = client.task.create(
        collaboration=args.collaboration,
        organizations=[min(orgs)],
        name="mixed-runtime sum",
        image=args.image,
        description="",
        method=args.compute_method,
        arguments=json.loads(args.compute_args),
        session=session["id"],
        databases=[{"dataframe_id": dataframe["id"]}],
        action="central_compute",
    )
    task = wait_for_task(client, task["id"], args.timeout)
    if task["status"] != TaskStatus.COMPLETED.value:
        fail(f"Central task {task['id']} failed")
    subtasks = client.task.list(parent=task["id"])["data"]
    for subtask in subtasks:
        check_runs(client, subtask["id"], orgs)
    if not subtasks:
        fail("The central task created no subtasks")
    print("federated compute completed on both nodes")

    results = client.result.from_task(task["id"])
    expected = expected_sum(args.column)
    if not contains_number(results, expected):
        fail(f"Result {results} does not contain the expected sum {expected}")
    print(f"result contains the expected sum {expected}")
    print("PASSED")


if __name__ == "__main__":
    main()
