import base64
import json
import logging
import queue
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

from vantage6.common import logger_name
from vantage6.common.globals import ENV_VAR_EQUALS_REPLACEMENT, STRING_ENCODING
from vantage6.common.task_status import TaskStatus
from vantage6.node.tes_relay.dare_client import DareSubmissionLayerClient


class RelayResult(NamedTuple):
    run_id: int
    task_id: int
    logs: str
    data: bytes
    status: TaskStatus
    parent_id: int | None


class KilledRun(NamedTuple):
    run_id: int
    task_id: int
    parent_id: int | None


@dataclass
class _RelayTask:
    run_id: int
    task_id: int
    parent_id: int | None
    tes_id: str
    created_at: float
    last_state: str | None = None


_DARE_NUMERIC_STATE = {
    0: "QUEUED",
    1: "QUEUED",
    2: "INITIALIZING",
    3: "RUNNING",
    4: "RUNNING",
    5: "RUNNING",
    6: "RUNNING",
    7: "RUNNING",
    8: "SYSTEM_ERROR",
    9: "SYSTEM_ERROR",
    10: "SYSTEM_ERROR",
    11: "COMPLETE",
    12: "SYSTEM_ERROR",
    13: "CANCELING",
    14: "CANCELING",
    15: "CANCELING",
    16: "CANCELED",
    17: "INITIALIZING",
    21: "INITIALIZING",
    22: "EXECUTOR_ERROR",
    25: "EXECUTOR_ERROR",
    26: "RUNNING",
    27: "EXECUTOR_ERROR",
    30: "RUNNING",
    31: "RUNNING",
    32: "RUNNING",
    33: "RUNNING",
    34: "RUNNING",
    35: "RUNNING",
    36: "RUNNING",
    37: "RUNNING",
    38: "RUNNING",
    39: "RUNNING",
    40: "RUNNING",
    41: "COMPLETE",
    42: "EXECUTOR_ERROR",
    43: "INITIALIZING",
    44: "INITIALIZING",
    45: "SYSTEM_ERROR",
    49: "COMPLETE",
}


def _safe_state(task: dict) -> str | None:
    state = task.get("state") or task.get("State")
    if state is None:
        return None
    if isinstance(state, int):
        return _DARE_NUMERIC_STATE.get(state, f"UNKNOWN({state})")
    if isinstance(state, dict):
        inner = state.get("state") or state.get("State")
        if isinstance(inner, int):
            return _DARE_NUMERIC_STATE.get(inner, f"UNKNOWN({inner})")
        return str(inner) if inner is not None else None
    return str(state)


def _is_terminal_state(state: str | None) -> bool:
    if not state:
        return False
    return state.strip().upper() in {
        "COMPLETE",
        "CANCELED",
        "EXECUTOR_ERROR",
        "SYSTEM_ERROR",
    }


def _map_state_to_v6_status(state: str | None) -> TaskStatus:
    if not state:
        return TaskStatus.ACTIVE
    s = state.strip().upper()
    if s == "COMPLETE":
        return TaskStatus.COMPLETED
    if s == "CANCELED":
        return TaskStatus.KILLED
    if s in {"EXECUTOR_ERROR", "SYSTEM_ERROR"}:
        return TaskStatus.FAILED
    return TaskStatus.ACTIVE


class TesRelayManager:
    """
    Drop-in replacement for :class:`DockerManager` that relays tasks to a
    GA4GH TES endpoint instead of running them locally in Docker containers.
    """

    def __init__(
        self,
        *,
        ctx: Any,
        isolated_network_mgr: Any,
        vpn_manager: Any,
        tasks_dir: Path,
        client: Any,
        proxy: Any = None,
    ) -> None:
        self.log = logging.getLogger(logger_name(__name__))
        self.ctx = ctx
        self.client = client
        self._tasks_dir = tasks_dir

        cfg = (ctx.config or {}).get("tes_relay") or {}
        self._cfg = cfg

        tes_endpoint = cfg.get("tes_endpoint")
        if not tes_endpoint:
            raise RuntimeError(
                "tes_relay.enabled is true but tes_relay.tes_endpoint is not set"
            )

        self._submission = DareSubmissionLayerClient.from_tes_relay_config(
            tes_endpoint=str(tes_endpoint),
            tes_relay_cfg=cfg,
        )

        self.active_tasks: list[_RelayTask] = []
        self.failed_tasks: list[_RelayTask] = []
        self._active_by_run_id: dict[int, _RelayTask] = {}

        self._results: queue.Queue[RelayResult] = queue.Queue()
        self._stop_event = threading.Event()

        self._poll_interval_s = float(cfg.get("poll_interval_seconds", 5))
        self._poll_view = str(cfg.get("poll_view", "MINIMAL")).upper()
        self._background_polling = bool(cfg.get("poll_in_background", True))

        if self._background_polling:
            t = threading.Thread(target=self._poll_loop, daemon=True)
            t.start()
            self._poll_thread = t
        else:
            self._poll_thread = None

    def is_running(self, run_id: int) -> bool:
        return int(run_id) in self._active_by_run_id

    def create_volume(self, volume_name: str) -> None:
        return

    def link_container_to_network(self, container_name: str, config_alias: str) -> None:
        return

    def get_column_names(self, label: str, type_: str) -> list[str]:
        return []

    def run(
        self,
        *,
        run_id: int,
        task_info: dict,
        image: str,
        docker_input: str,
        tmp_vol_name: str,
        token: str,
        databases_to_use: list[str],
        socketIO: Any,
    ) -> tuple[TaskStatus, None]:
        _ = tmp_vol_name, token, databases_to_use, socketIO
        cfg = self._cfg

        dare_cfg = cfg.get("dare") or {}
        bucket_name = self._submission.resolve_submission_bucket(dare_cfg=dare_cfg)

        tags = cfg.get("tags") or {}
        if not isinstance(tags, dict) or not tags:
            raise _RelayConfigError(
                "tes_relay.tags must be a mapping and include at least "
                "'project' and 'tres' for the DARE demo"
            )

        try:
            _, tes_id = self._relay_v6_env(
                run_id=int(run_id),
                task_info=task_info,
                image=str(image),
                docker_input=str(docker_input),
                bucket_name=str(bucket_name),
                tags=tags,
            )
        except _RelayConfigError as e:
            msg = str(e)
            self._results.put(
                RelayResult(
                    run_id=int(run_id),
                    task_id=int(task_info["id"]),
                    logs=msg,
                    data=msg.encode("utf-8"),
                    status=TaskStatus.FAILED,
                    parent_id=None,
                )
            )
            return TaskStatus.FAILED, None

        rec = _RelayTask(
            run_id=int(run_id),
            task_id=int(task_info["id"]),
            parent_id=(
                task_info.get("parent", {}).get("id")
                if isinstance(task_info.get("parent"), dict)
                else None
            ),
            tes_id=str(tes_id),
            created_at=time.time(),
        )
        self.active_tasks.append(rec)
        self._active_by_run_id[rec.run_id] = rec

        self.log.info(
            "Relayed run_id=%s task_id=%s to TES submission_id=%s",
            rec.run_id,
            rec.task_id,
            rec.tes_id,
        )
        return TaskStatus.ACTIVE, None

    def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self.poll_once()
            except Exception:
                self.log.exception("TES relay poll loop exception")
            self._stop_event.wait(self._poll_interval_s)

    def poll_once(self) -> None:
        for run_id, rec in list(self._active_by_run_id.items()):
            dare_status = self._submission.get_submission_status(rec.tes_id)
            if dare_status is not None:
                state = _DARE_NUMERIC_STATE.get(dare_status, f"UNKNOWN({dare_status})")
            else:
                task = self._submission.tes.get_task(rec.tes_id, view=self._poll_view)
                state = _safe_state(task)

            if state and state != rec.last_state:
                self.log.info(
                    "TES task state update: submission_id=%s state=%s (dare_status=%s)",
                    rec.tes_id,
                    state,
                    dare_status,
                )
                rec.last_state = state

            if not _is_terminal_state(state):
                continue

            status = _map_state_to_v6_status(state)
            payload = {
                "tes": {
                    "id": rec.tes_id,
                    "state": state,
                    "dare_status": dare_status,
                }
            }
            result = RelayResult(
                run_id=rec.run_id,
                task_id=rec.task_id,
                logs=f"TES relay submission_id={rec.tes_id} state={state}",
                data=json.dumps(payload).encode("utf-8"),
                status=status,
                parent_id=rec.parent_id,
            )
            self._results.put(result)

            self._active_by_run_id.pop(rec.run_id, None)
            try:
                self.active_tasks.remove(rec)
            except ValueError:
                pass

    def get_result(self, timeout: float | None = None) -> RelayResult:
        return self._results.get(timeout=timeout)

    def kill_tasks(
        self, org_id: int, kill_list: list[dict] | None = None
    ) -> list[KilledRun]:
        killed: list[KilledRun] = []
        if kill_list:
            to_kill = [
                k for k in kill_list if int(k.get("organization_id", -1)) == int(org_id)
            ]
        else:
            to_kill = [
                {"run_id": rid, "organization_id": org_id}
                for rid in self._active_by_run_id
            ]

        for k in to_kill:
            run_id = int(k.get("run_id"))
            rec = self._active_by_run_id.get(run_id)
            if not rec:
                continue
            try:
                self._submission.tes.cancel_task(rec.tes_id)
            except Exception:
                self.log.exception("Failed cancelling TES submission_id=%s", rec.tes_id)
            killed.append(
                KilledRun(
                    run_id=rec.run_id,
                    task_id=rec.task_id,
                    parent_id=rec.parent_id,
                )
            )
            self._active_by_run_id.pop(rec.run_id, None)
            try:
                self.active_tasks.remove(rec)
            except ValueError:
                pass
        return killed

    def cleanup(self) -> list[KilledRun]:
        self._stop_event.set()
        killed: list[KilledRun] = []
        for rec in list(self._active_by_run_id.values()):
            try:
                self._submission.tes.cancel_task(rec.tes_id)
            except Exception:
                self.log.exception("Failed cancelling TES submission_id=%s", rec.tes_id)
            killed.append(
                KilledRun(
                    run_id=rec.run_id,
                    task_id=rec.task_id,
                    parent_id=rec.parent_id,
                )
            )
        self._active_by_run_id.clear()
        self.active_tasks.clear()
        return killed

    def _relay_v6_env(
        self,
        *,
        run_id: int,
        task_info: dict,
        image: str,
        docker_input: str,
        bucket_name: str,
        tags: dict,
    ) -> tuple[dict, str]:
        cfg = self._cfg

        data_dir = str(cfg.get("data_dir", "/data")).rstrip("/")
        task_folder_name = f"task-{run_id:09d}"
        task_dir = f"{data_dir}/{task_folder_name}"
        input_path = f"{task_dir}/input"
        output_path = f"{task_dir}/output"

        self._submission.upload_to_minio(
            bucket_name=bucket_name,
            object_name=input_path.lstrip("/"),
            content_bytes=docker_input.encode("utf-8"),
        )

        requested_dbs = task_info.get("databases", []) or []
        db_labels = []
        for db in requested_dbs:
            if isinstance(db, dict) and db.get("label"):
                db_labels.append(str(db["label"]))
        user_labels = ",".join(db_labels)

        env_plain: dict[str, str] = {
            "INPUT_FILE": input_path,
            "OUTPUT_FILE": output_path,
            "TEMPORARY_FOLDER": str(cfg.get("temporary_folder", "/tmp")),
            "USER_REQUESTED_DATABASE_LABELS": user_labels,
        }

        db_map = cfg.get("databases_map", None)
        if not isinstance(db_map, dict) or not db_map:
            raise _RelayConfigError(
                "tes_relay.databases_map must be a non-empty mapping "
                "(label -> in-container path)"
            )

        for label in db_labels:
            uri = db_map.get(label)
            if not uri:
                raise _RelayConfigError(
                    f"No databases_map entry for requested database label '{label}'"
                )
            env_plain[f"{label.upper()}_DATABASE_URI"] = str(uri)
            env_plain[f"{label.upper()}_DATABASE_TYPE"] = "csv"

        env_encoded = {k: _encode_env_value(v) for k, v in env_plain.items()}

        if not isinstance(tags, dict) or not tags:
            raise _RelayConfigError("tes_relay.tags must be a non-empty mapping")

        command = cfg.get("command")
        if command is not None:
            if not isinstance(command, list) or not all(
                isinstance(x, str) for x in command
            ):
                raise RuntimeError(
                    "tes_relay.command must be a list of strings or null"
                )
            executor = {"image": image, "command": command, "env": env_encoded}
        else:
            executor = {"image": image, "env": env_encoded}

        v6_desc = None
        if isinstance(task_info, dict):
            v6_desc = task_info.get("description") or task_info.get("Description")
        description = (
            f"[Vantage6-TES-relay] {v6_desc}" if v6_desc else "[Vantage6-TES-relay]"
        )

        tes_task = {
            "name": f"v6-relay run={run_id} task={task_info.get('id')}",
            "description": description,
            "executors": [executor],
            "inputs": [
                {
                    "name": "v6_input",
                    "description": "Vantage6 algorithm input",
                    "path": input_path,
                    "url": input_path,
                    "content": "",
                    "type": "FILE",
                },
            ],
            "outputs": [
                {
                    "name": "v6_output",
                    "description": "Vantage6 algorithm output",
                    "path": output_path,
                    "url": output_path,
                    "type": "FILE",
                },
            ],
            "tags": tags,
        }

        tes_id = self._submission.tes.create_task(tes_task)
        return tes_task, tes_id


class _RelayConfigError(RuntimeError):
    pass


def _encode_env_value(value: str) -> str:
    return (
        base64.b32encode(str(value).encode(STRING_ENCODING))
        .decode(STRING_ENCODING)
        .replace("=", ENV_VAR_EQUALS_REPLACEMENT)
    )
