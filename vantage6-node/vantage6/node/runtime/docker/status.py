from vantage6.node.runtime.base import RunState


def container_state(attrs: dict) -> tuple[RunState, int | None, str | None]:
    """Map ``docker inspect`` output to a run state, exit code and failure reason."""
    state = attrs.get("State") or {}
    status = state.get("Status")
    if status == "created":
        return RunState.PENDING, None, None
    if status in ("running", "restarting", "paused", "removing"):
        return RunState.RUNNING, None, None

    exit_code = state.get("ExitCode")
    if state.get("OOMKilled"):
        return RunState.FAILED, exit_code, "OOMKilled"
    if status == "exited" and exit_code == 0:
        return RunState.SUCCEEDED, 0, None
    return RunState.FAILED, exit_code, state.get("Error") or None
