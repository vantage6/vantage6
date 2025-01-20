from vantage6.server.model import Run
from vantage6.server.model.base import DatabaseSessionManager
from datetime import datetime, timedelta, timezone
import logging

module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def cleanup_results(days: int):
    """
    Clear the `result` field for `Run` instances older than the specified number of days.

    Parameters
    ----------
    days : int
        The number of days after which results should be cleared.
    """
    threshold_date = datetime.now(timezone.utc) - timedelta(days=days)
    session = DatabaseSessionManager.get_session()

    if not days or days < 1:
        log.warning("Invalid number of days specified. No cleanup will be performed.")
        return

    try:
        with session.begin():
            runs = session.query(Run).filter(Run.finished_at < threshold_date).all()
            for run in runs:
                run.result = ""
                log.info(f"Cleared result for Run ID {run.id}.")

        log.info(
            "Cleanup job completed successfully, deleted %d old run results.", len(runs)
        )
    except Exception as e:
        log.error(f"Failed to cleanup old run results: {e}")
        raise
