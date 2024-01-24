import logging

from pathlib import Path


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
    fh = logging.handlers.RotatingFileHandler(file_path)
    fh.setLevel(log_level_file)
    logger.addHandler(fh)

    # add custom console handler
    ch = logging.StreamHandler()
    ch.setLevel(log_level_console)
    logger.addHandler(ch)

    logger.setLevel(log_level_file)
    return logger
