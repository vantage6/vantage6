import logging

from datetime import datetime, timedelta, timezone

from vantage6.common.task_status import TaskStatus
from vantage6.server.model import Run
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.service.storage_adapter import StorageAdapter

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def cleanup_runs_data(
    config: dict,
    storage_adapter: StorageAdapter | None = None,
    include_input: bool = False,
):
    """
    Clear the `result` and (optionally) `input` field for `Run` instances older
    than the specified number of days.

    Parameters
    ----------
    config : dict
        Server configuration.
    storage_adapter : StorageAdapter | None
        Adapter for the large run-data store, or None when it is not
        configured. Supplied by the caller rather than built here: this
        function runs on an hourly loop, and constructing an adapter per
        call would leave behind an extra backend client every time.
    include_input : bool
        Whether to clear the `input` field as well as the `result` field.
    """
    days = config.get("runs_data_cleanup_days")
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    session = DatabaseSessionManager.get_session()

    if not days or days < 1:
        log.warning(
            "Invalid number of days '%s' specified. No cleanup will be performed.", days
        )
        return

    try:
        with session.begin():
            runs = (
                session.query(Run)
                .filter(
                    Run.finished_at < threshold_date,
                    Run.cleanup_at == None,
                    Run.status == TaskStatus.COMPLETED,
                )
                .all()
            )

            for run in runs:
                if (
                    run.result is not None
                    and run.blob_storage_used == True
                    and storage_adapter
                ):
                    log.debug(f"Deleting run data: {run.result}")
                    try:
                        storage_adapter.delete_run_data(run.result)
                    except Exception as e:
                        log.warning(f"Failed to delete result {run.result}: {e}")
                run.result = ""
                if include_input:
                    if (
                        run.input is not None
                        and run.blob_storage_used == True
                        and storage_adapter
                    ):
                        log.debug(f"Deleting run data: {run.input}")
                        try:
                            storage_adapter.delete_run_data(run.input)
                        except Exception as e:
                            log.warning(f"Failed to delete input {run.input}: {e}")
                    run.input = ""
                run.cleanup_at = datetime.now(timezone.utc)
                log.info(f"Cleared result for Run ID {run.id}.")

        log.info(
            "Cleanup job completed successfully, deleted %d old run results.", len(runs)
        )
    except Exception as e:
        log.error(f"Failed to cleanup old run results: {e}")
        raise
