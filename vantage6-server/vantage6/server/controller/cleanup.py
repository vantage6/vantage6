import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from vantage6.common.enum import RunStatus

from vantage6.server.model import Run
from vantage6.server.model.base import DatabaseSessionManager

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def cleanup_runs_data(days: int, include_args: bool = False):
    """
    Clear the `result` and (optionally) `arguments` field for `Run` instances older
    than the specified number of days.

    Parameters
    ----------
    days : int
        The number of days after which results should be cleared.
    """
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    session = DatabaseSessionManager.get_session()

    if not days or days < 1:
        log.warning(
            "Invalid number of days '%s' specified. No cleanup will be performed.", days
        )
        return

    try:
        with session.begin():
            # Using select() instead of query()
            runs = session.scalars(
                select(Run).filter(
                    Run.finished_at < threshold_date,
                    Run.cleanup_at == None,
                    Run.status == RunStatus.COMPLETED,
                )
            ).all()
            for run in runs:
                run.result = ""
                if include_args:
                    run.arguments = ""
                run.cleanup_at = datetime.now(timezone.utc)
                log.info("Cleared result for Run ID %s.", run.id)

        log.info(
            "Cleanup job completed successfully, deleted %d old run results.", len(runs)
        )
    except Exception as e:
        log.error("Failed to cleanup old run results: %s", e)
        raise
