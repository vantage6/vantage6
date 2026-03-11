import logging
import logging.handlers
import os

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FileMetadata:
    user_id: int
    group_id: int
    mode: int


class OwnershipPreservingRotatingFileHandler(logging.handlers.RotatingFileHandler):
    """
    Rotating file handler that keeps ownership and mode after rollover.

    This prevents permission issues when the same mounted log file may be
    created by a regular host user (e.g. id=1000), but rotate by root inside a
    container.
    """

    def _capture_metadata(self) -> FileMetadata | None:
        try:
            file_stats = os.stat(self.baseFilename)
        except OSError:
            return None
        return FileMetadata(
            user_id=file_stats.st_uid,
            group_id=file_stats.st_gid,
            mode=file_stats.st_mode & 0o7777,
        )

    def _restore_metadata(self, metadata: FileMetadata | None) -> None:
        if not metadata:
            return
        try:
            os.chown(self.baseFilename, metadata.user_id, metadata.group_id)
        except OSError:
            pass
        try:
            os.chmod(self.baseFilename, metadata.mode)
        except OSError:
            pass

    def doRollover(self) -> None:
        """
        Rotate the active log file and restore its original ownership and mode.

        Overrides ``logging.handlers.RotatingFileHandler.doRollover()`` so the
        replacement log file keeps the same uid, gid, and permissions as the
        pre-rollover file.
        """
        metadata = self._capture_metadata()
        super().doRollover()
        self._restore_metadata(metadata)


def get_file_logger(
    logger_name: str,
    file_path: Path | str,
    log_level_file: int = logging.DEBUG,
    log_level_console: int = logging.WARN,
) -> logging.Logger:
    """
    Create a logger that primarily writes to a file.

    It overwrites the root logger settings to prevent console logging that is
    set by default log configuration settings.

    Parameters
    ----------
    logger_name: str
        Name of the logger
    file_path: Path | str
        Path to the log file
    log_level_file: int
        Log level for file output. Default is logging.DEBUG
    log_level_console: int
        Log level for console output. Default is logging.WARN

    Returns
    -------
    logging.Logger
    """
    logger = logging.getLogger(logger_name)

    # overwrite root logger settings to prevent console logging
    logger.propagate = False

    # add file handler
    fh = OwnershipPreservingRotatingFileHandler(file_path)
    fh.setLevel(log_level_file)
    logger.addHandler(fh)

    # add custom console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level_console)
    logger.addHandler(ch)

    logger.setLevel(log_level_file)
    return logger
