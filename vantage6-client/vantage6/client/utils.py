from vantage6.common.enum import StrEnumBase


class LogLevel(StrEnumBase):
    """
    Enum for the different log levels

    Attributes
    ----------
    DEBUG: str
        The debug log level
    INFO: str
        The info log level
    WARN: str
        The warn log level
    ERROR: str
        The error log level
    CRITICAL: str
        The critical log level
    """

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
