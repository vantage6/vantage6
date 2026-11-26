"""Fixed inputs for the golden Kubernetes Job test."""

from unittest.mock import MagicMock

from vantage6.common.dataclass import TaskDB
from vantage6.common.enum import AlgorithmStepType, DatabaseMountMode

ENV = {
    "V6_PROXY_HOST": "http://rel.tenant.svc.cluster.local",
    "V6_PROXY_PORT": "7676",
}

CONFIG = {
    "task_storage": {
        "claim_name": "tasks-pvc",
        "sub_path": "node-a",
        "colocate_with_node": True,
    },
    "node_pod_labels": {"app": "vantage6-node", "release": "rel"},
    "release_name": "rel",
    "task_namespace": "tenant",
    "algorithm_pods": {
        "resources": {"limits": {"cpu": "1", "memory": "1Gi"}},
        "security_context": {"runAsNonRoot": True},
        "pod_security_context": {"fsGroup": 0},
        "runtime_class_name": "gvisor",
        "service_account_name": "algo",
        "ttl_seconds_after_finished": 600,
    },
    "algorithm_env": {"threshold": "10"},
    "private_docker_registries": [
        {"registry": "reg.example.org", "username": "u", "password": "p"}
    ],
    "policies": {"require_algorithm_pull": False},
}

DATABASES = {
    "csv": TaskDB(
        label="csv",
        type="csv",
        uri="/app/databases/csv.csv",
        local_uri="/app/databases/csv.csv",
        is_file=True,
        is_dir=False,
        env={"user": "reader"},
        mount_mode=DatabaseMountMode.READ_ONLY,
        claim_name="data-pvc",
        sub_path="hospital/data.csv",
    ),
}

CASES = {
    "data_extraction": {
        "run_id": 101,
        "action": AlgorithmStepType.DATA_EXTRACTION,
        "databases_to_use": [{"label": "csv", "type": "source"}],
        "dataframe": {"name": "df1", "id": 3, "label": "csv"},
        "token": "",
    },
    "federated_compute": {
        "run_id": 102,
        "action": AlgorithmStepType.FEDERATED_COMPUTE,
        "databases_to_use": [
            {"type": "dataframe", "dataframe_name": "df1", "position": 0},
            {"type": "dataframe", "dataframe_name": "df2", "position": 1},
        ],
        "dataframe": None,
        "token": "",
    },
    "central_compute": {
        "run_id": 103,
        "action": AlgorithmStepType.CENTRAL_COMPUTE,
        "databases_to_use": [
            {"type": "dataframe", "dataframe_name": "df1", "position": 0}
        ],
        "dataframe": None,
        "token": "container-token",
    },
}


def make_ctx() -> MagicMock:
    ctx = MagicMock()
    ctx.config = CONFIG
    ctx.identifier = "abc123"
    return ctx


def make_client() -> MagicMock:
    client = MagicMock()
    client.whoami.id_ = 11
    client.whoami.organization_id = 22
    client.collaboration_id = 33
    return client


def make_run_io(run_id, session_id, action, client, df_details, **_kwargs):
    run_io = MagicMock()
    run_io.run_id = run_id
    run_io.action = action
    run_io.container_name = f"vantage6-run-{run_id}"
    run_io.create_files.return_value = (f"{run_id}/input", f"{run_id}/output")
    run_io.session_file_manager.session_folder = f"sessions/session{session_id:09d}"
    run_io.session_file_manager.session_state_file_name = "state.parquet"
    return run_io


def task_info(case: dict) -> dict:
    info = {
        "id": 500 + case["run_id"],
        "init_org": {"id": 1},
        "init_user": {"id": 2},
        "method": "my_method",
        "parent": None,
    }
    if case["dataframe"]:
        info["dataframe"] = case["dataframe"]
    return info
