"""
Render the node chart with the value files in ``values/`` and check that each
scenario only produces what its cluster allows. Needs ``helm`` and PyYAML.

    python charts/node/tests/check_render.py
"""

import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterator
from pathlib import Path

import yaml

CHARTS_DIR = Path(__file__).resolve().parents[2]
VALUES_DIR = Path(__file__).resolve().parent / "values"
RELEASE = "test-node"
NAMESPACE = "tenant"

CLUSTER_SCOPED_KINDS = {
    "PersistentVolume",
    "StorageClass",
    "Namespace",
    "ClusterRole",
    "ClusterRoleBinding",
}
HOST_BOUND_KEYS = {"hostPath", "local", "nodeAffinity", "nodeName", "hostNetwork"}
RESOURCE_NAMES = ("cpu", "memory", "ephemeral-storage")


def render(chart: Path, values: Path) -> list[dict]:
    subprocess.run(
        ["helm", "lint", str(chart), "-f", str(values), "--namespace", NAMESPACE],
        check=True,
        capture_output=True,
        text=True,
    )
    out = subprocess.run(
        [
            "helm",
            "template",
            RELEASE,
            str(chart),
            "-f",
            str(values),
            "--namespace",
            NAMESPACE,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [doc for doc in yaml.safe_load_all(out) if doc]


def walk(obj, path: str = "") -> Iterator[tuple[str, str, object]]:
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield path, key, value
            yield from walk(value, f"{path}.{key}")
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            yield from walk(value, f"{path}[{idx}]")


def of_kind(docs: list[dict], kind: str) -> list[dict]:
    return [doc for doc in docs if doc["kind"] == kind]


def node_config(docs: list[dict]) -> dict:
    return yaml.safe_load(of_kind(docs, "ConfigMap")[0]["data"]["config.yml"])


def pod_specs(docs: list[dict]) -> list[dict]:
    return [doc["spec"]["template"]["spec"] for doc in of_kind(docs, "Deployment")]


def assert_restricted(docs: list[dict]) -> None:
    kinds = {doc["kind"] for doc in docs}
    assert not kinds & CLUSTER_SCOPED_KINDS, kinds & CLUSTER_SCOPED_KINDS
    for doc in docs:
        assert doc["metadata"].get("namespace") == NAMESPACE, doc["metadata"]
        for path, key, _ in walk(doc):
            assert key not in HOST_BOUND_KEYS, f"{doc['kind']}{path}.{key}"
    for claim in of_kind(docs, "PersistentVolumeClaim"):
        assert "selector" not in claim["spec"], claim["metadata"]["name"]
    for spec in pod_specs(docs):
        for container in spec["containers"]:
            for kind in ("requests", "limits"):
                for name in RESOURCE_NAMES:
                    assert name in container.get("resources", {}).get(kind, {}), (
                        container["name"],
                        kind,
                        name,
                    )
    resources = node_config(docs)["algorithm_pods"]["resources"]
    for kind in ("requests", "limits"):
        assert set(resources[kind]) == set(RESOURCE_NAMES), resources


def database_volume(docs: list[dict]) -> dict:
    spec = pod_specs(docs)[0]
    volume = next(v for v in spec["volumes"] if v["name"].startswith("database-"))
    mount = next(
        m for m in spec["containers"][0]["volumeMounts"] if m["name"] == volume["name"]
    )
    return {"claim": volume["persistentVolumeClaim"]["claimName"], **mount}


def check_restricted(docs: list[dict]) -> None:
    assert_restricted(docs)
    config = node_config(docs)
    assert config["task_namespace"] == NAMESPACE
    assert config["task_storage"] == {
        "claim_name": f"{RELEASE}-task-pvc",
        "sub_path": "",
        "colocate_with_node": True,
    }, config["task_storage"]
    assert config["node_pod_labels"]["component"] == "node"
    assert config["algorithm_pods"]["ttl_seconds_after_finished"] == 86400
    assert config["network_isolation"]["verify"] is True
    assert of_kind(docs, "Deployment")[0]["spec"]["strategy"]["type"] == "Recreate"
    db = database_volume(docs)
    assert db["claim"] == "hospital-data", db
    assert db["subPath"] == "exports/data.csv", db
    assert db["readOnly"] is True, db
    policies = {
        p["metadata"]["name"]: p["spec"] for p in of_kind(docs, "NetworkPolicy")
    }
    default_deny = policies[f"{RELEASE}-tasks-default-policy"]
    assert default_deny["podSelector"]["matchLabels"] == {
        "v6-pod-type": "algorithm",
        "v6-node-release": RELEASE,
    }, default_deny


def check_dsri(docs: list[dict]) -> None:
    assert_restricted(docs)
    config = node_config(docs)
    assert config["task_storage"]["colocate_with_node"] is False
    assert config["algorithm_pods"]["service_account_name"] == "anyuid"
    assert config["algorithm_pods"]["runtime_class_name"] == "selinux"
    assert pod_specs(docs)[0]["runtimeClassName"] == "selinux"
    task_claim = next(
        c
        for c in of_kind(docs, "PersistentVolumeClaim")
        if c["metadata"]["name"] == f"{RELEASE}-task-pvc"
    )
    assert task_claim["spec"]["accessModes"] == ["ReadWriteMany"]
    assert task_claim["spec"]["storageClassName"] == "ocs-storagecluster-cephfs"
    central = next(
        p["spec"]
        for p in of_kind(docs, "NetworkPolicy")
        if p["metadata"]["name"] == f"{RELEASE}-central-compute-policy"
    )
    dns = central["egress"][1]
    assert dns["to"][0]["namespaceSelector"]["matchLabels"] == {
        "kubernetes.io/metadata.name": "openshift-dns"
    }, dns
    assert {p["port"] for p in dns["ports"]} == {5353}, dns


def check_no_netpol(docs: list[dict]) -> None:
    assert not of_kind(docs, "NetworkPolicy")
    assert not of_kind(docs, "PersistentVolumeClaim"), "existing claim is reused"
    config = node_config(docs)
    assert config["network_isolation"]["verify"] is False
    assert config["task_storage"]["claim_name"] == "vantage6-tasks"
    spec = pod_specs(docs)[0]
    logs = next(v for v in spec["volumes"] if v["name"] == "node-logs")
    assert logs == {"name": "node-logs", "emptyDir": {}}, logs
    task_mount = next(
        m
        for m in spec["containers"][0]["volumeMounts"]
        if m["name"] == "task-files-root"
    )
    assert task_mount["subPath"] == "node-1", task_mount


def check_dev_static(docs: list[dict]) -> None:
    kinds = [doc["kind"] for doc in docs]
    assert kinds.count("PersistentVolume") == 3, kinds
    assert "StorageClass" in kinds
    assert "ClusterRole" not in kinds and "Namespace" not in kinds
    config = node_config(docs)
    assert config["task_storage"]["colocate_with_node"] is False
    db = database_volume(docs)
    assert db["claim"] == f"{RELEASE}-db-pvc-olympic-athletes", db
    assert db["subPath"] == "olympic_athletes_2016.csv", db
    central = next(
        p["spec"]
        for p in of_kind(docs, "NetworkPolicy")
        if p["metadata"]["name"] == f"{RELEASE}-central-compute-policy"
    )
    assert [p["port"] for p in central["egress"][0]["ports"]] == [7654, 7655, 7656]


SCENARIOS: dict[str, Callable[[list[dict]], None]] = {
    "restricted.yaml": check_restricted,
    "dsri.yaml": check_dsri,
    "no-netpol.yaml": check_no_netpol,
    "dev-static.yaml": check_dev_static,
}


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        # Work on a copy, so that resolving the dependency leaves the repository alone
        for name in ("node", "common"):
            shutil.copytree(CHARTS_DIR / name, Path(tmp) / name)
        chart = Path(tmp) / "node"
        subprocess.run(
            ["helm", "dependency", "update", str(chart)],
            check=True,
            capture_output=True,
        )
        failures = 0
        for values_file, check in SCENARIOS.items():
            try:
                check(render(chart, VALUES_DIR / values_file))
            except subprocess.CalledProcessError as exc:
                failures += 1
                print(f"FAIL {values_file}: {exc.stdout}{exc.stderr}")
            except (AssertionError, KeyError, IndexError, StopIteration) as exc:
                failures += 1
                print(f"FAIL {values_file}: {exc!r}")
            else:
                print(f"ok   {values_file}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
