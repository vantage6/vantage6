from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import ClassVar, Self

from vantage6.common.enum import AlgorithmStepType, RunStatus

from vantage6.cli.context.node import NodeContext


class StorageKind(StrEnum):
    # The node's task storage, mounted in the node container at TASK_FILES_ROOT
    TASK = "task"
    # A Kubernetes PersistentVolumeClaim
    CLAIM = "claim"
    # A path on the container host
    HOST_PATH = "host_path"


class RunState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"

    @property
    def is_finished(self) -> bool:
        return self in (RunState.SUCCEEDED, RunState.FAILED)


class PullPolicy(StrEnum):
    ALWAYS = "always"
    IF_NOT_PRESENT = "if_not_present"


@dataclass(frozen=True)
class StorageRef:
    kind: StorageKind
    # Claim name or host path; unused for TASK
    name: str | None = None


@dataclass(frozen=True)
class MountSpec:
    storage: StorageRef
    # Path inside the storage, relative to its root
    sub_path: str
    target: str
    read_only: bool = False


@dataclass(frozen=True)
class RegistryCredentials:
    registry: str
    username: str
    password: str


@dataclass(frozen=True)
class RunMetadata:
    """Run details stored with the run in the runtime, to recover it later."""

    run_id: int
    task_id: int
    task_parent_id: int | None
    init_org_id: int
    action: AlgorithmStepType
    session_id: int
    df_name: str = ""
    df_id: str = ""
    df_label: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": str(self.run_id),
            "task_id": str(self.task_id),
            "task_parent_id": str(self.task_parent_id) if self.task_parent_id else "",
            "init_org_id": str(self.init_org_id),
            "action": self.action.value,
            "session_id": str(self.session_id),
            "df_name": self.df_name or "",
            "df_id": self.df_id or "",
            "df_label": self.df_label or "",
        }

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> Self:
        parent = data.get("task_parent_id")
        return cls(
            run_id=int(data["run_id"]),
            task_id=int(data["task_id"]),
            task_parent_id=int(parent) if parent else None,
            init_org_id=int(data["init_org_id"]),
            action=AlgorithmStepType(data["action"]),
            session_id=int(data["session_id"]),
            df_name=data.get("df_name") or "",
            df_id=data.get("df_id") or "",
            df_label=data.get("df_label") or "",
        )


@dataclass(frozen=True)
class RunSpec:
    name: str
    image: str
    step: AlgorithmStepType
    # Already encoded by the container manager
    env: dict[str, str]
    # Passed to the algorithm as is, kept out of labels and logs
    secret_env: dict[str, str]
    mounts: list[MountSpec]
    metadata: RunMetadata
    pull_policy: PullPolicy = PullPolicy.ALWAYS
    registries: list[RegistryCredentials] = field(default_factory=list)


@dataclass(frozen=True)
class RunInfo:
    name: str
    state: RunState
    metadata: RunMetadata
    exit_code: int | None = None
    # Why the run failed, if the runtime knows, e.g. "OOMKilled"
    reason: str | None = None


class ContainerRuntime(ABC):
    """Runs algorithm containers on a container platform."""

    name: ClassVar[str]

    def __init__(self, ctx: NodeContext) -> None:
        self.ctx = ctx

    @abstractmethod
    def describe(self) -> str:
        """Where algorithms run, for log messages."""

    def prepare(self) -> None:
        """Create the helper resources algorithms need. Must be idempotent."""

    @abstractmethod
    def preflight(self) -> tuple[bool, str]:
        """Check that algorithm containers can be started."""

    @abstractmethod
    def verify_isolation(self) -> tuple[bool, str]:
        """Check that central compute containers cannot reach the internet."""

    @abstractmethod
    def start_run(
        self, spec: RunSpec, on_status_change: Callable[[RunStatus], None]
    ) -> RunStatus:
        """
        Start a run and wait until it is active or has ended.

        A run that is returned as ACTIVE, FAILED or COMPLETED stays listed until
        ``remove_run``. For any other status the runtime removes what it created.
        """

    @abstractmethod
    def list_runs(self) -> list[RunInfo]:
        """All runs of this node, in any state."""

    @abstractmethod
    def run_exists(self, name: str) -> bool:
        pass

    @abstractmethod
    def logs(self, name: str) -> str:
        pass

    @abstractmethod
    def stream_logs(self, name: str) -> Iterator[str]:
        pass

    @abstractmethod
    def remove_run(self, name: str, run_id: int) -> None:
        """Stop the run if needed and delete everything created for it."""

    @abstractmethod
    def host_reachable_url(self, url: str) -> str:
        """Rewrite a localhost URL so that the node container can reach it."""

    def cleanup(self) -> None:
        """Remove the helper resources created by ``prepare``."""
