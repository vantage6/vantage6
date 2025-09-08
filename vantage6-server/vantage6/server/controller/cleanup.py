import logging

from datetime import datetime, timedelta, timezone

from vantage6.common.task_status import TaskStatus
from vantage6.server.model import Run
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.service.azure_storage_service import AzureStorageService

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def cleanup_runs_data(days: int, azure_config, include_input: bool = False):
    """
    Clear the `result` and (optionally) `input` field for `Run` instances older
    than the specified number of days.

    Parameters
    ----------
    days : int
        The number of days after which results should be cleared.
    """
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    session = DatabaseSessionManager.get_session()
    storage_adapter = AzureStorageService(
        container_name=azure_config.get("container_name"),
        blob_service_client=azure_config.get("blob_service_client")
    )

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
                ):
                    log.debug(f"Deleting blob: {run.result}")
                    storage_adapter.delete_blob(run.result)
                run.result = ""
                if include_input:
                    run.input = ""
                run.cleanup_at = datetime.now(timezone.utc)
                log.info(f"Cleared result for Run ID {run.id}.")

        log.info(
            "Cleanup job completed successfully, deleted %d old run results.", len(runs)
        )
    except Exception as e:
        log.error(f"Failed to cleanup old run results: {e}")
        raise
