# colored stream handler for python logging framework (use the
# ColorStreamHandler class).
#
# based on:
# http://stackoverflow.com/questions/384076/
# how-can-i-color-python-logging-output/1336640#1336640

# how to use:
# i used a dict-based logging configuration, not sure what else would work.
#
# import logging, logging.config, colorstreamhandler
#
# _LOGCONFIG = {
#     "version": 1,
#     "disable_existing_loggers": False,
#
#     "handlers": {
#         "console": {
#             "class": "colorstreamhandler.ColorStreamHandler",
#             "stream": "ext://sys.stderr",
#             "level": "INFO"
#         }
#     },
#
#     "root": {
#         "level": "INFO",
#         "handlers": ["console"]
#     }
# }
#
# logging.config.dictConfig(_LOGCONFIG)
# mylogger = logging.getLogger("mylogger")
# mylogger.warning("foobar")

# Copyright (c) 2014 Markus Pointner
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import logging
import platform

from typing import Any


class _AnsiColorStreamHandler(logging.StreamHandler):
    """
    Handler for logging colors to a stream, for example sys.stderr or
    sys.stdout.

    This handler is used for non-Windows systems.
    """

    DEFAULT = "\x1b[0m"
    RED = "\x1b[31m"
    GREEN = "\x1b[32m"
    YELLOW = "\x1b[33m"
    CYAN = "\x1b[36m"

    CRITICAL = RED
    ERROR = RED
    WARNING = YELLOW
    INFO = GREEN
    DEBUG = CYAN

    @classmethod
    def _get_color(cls, level: int) -> str:
        """
        Define which color to print for each log level.

        Parameters
        ----------
        level: int
            The log level.

        Returns
        -------
        str
            The color to print.
        """
        if level >= logging.CRITICAL:
            return cls.CRITICAL
        elif level >= logging.ERROR:
            return cls.ERROR
        elif level >= logging.WARNING:
            return cls.WARNING
        elif level >= logging.INFO:
            return cls.INFO
        elif level >= logging.DEBUG:
            return cls.DEBUG
        else:
            return cls.DEFAULT

    def __init__(self, stream: Any | None = None) -> None:
        """
        Initialize the handler.

        Parameters
        ----------
        stream: Any | None
            The stream to write to. If None, sys.stderr is used.
        """
        logging.StreamHandler.__init__(self, stream)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the log record.

        Parameters
        ----------
        record: logging.LogRecord
            The log record to format.

        Returns
        -------
        str
            The formatted log record.
        """
        text = logging.StreamHandler.format(self, record)
        color = self._get_color(record.levelno)
        return color + text + self.DEFAULT


class _WinColorStreamHandler(logging.StreamHandler):
    """Color stream handler for Windows systems."""

    # wincon.h
    FOREGROUND_BLACK = 0x0000
    FOREGROUND_BLUE = 0x0001
    FOREGROUND_GREEN = 0x0002
    FOREGROUND_CYAN = 0x0003
    FOREGROUND_RED = 0x0004
    FOREGROUND_MAGENTA = 0x0005
    FOREGROUND_YELLOW = 0x0006
    FOREGROUND_GREY = 0x0007
    FOREGROUND_INTENSITY = 0x0008  # foreground color is intensified.
    FOREGROUND_WHITE = FOREGROUND_BLUE | FOREGROUND_GREEN | FOREGROUND_RED

    BACKGROUND_BLACK = 0x0000
    BACKGROUND_BLUE = 0x0010
    BACKGROUND_GREEN = 0x0020
    BACKGROUND_CYAN = 0x0030
    BACKGROUND_RED = 0x0040
    BACKGROUND_MAGENTA = 0x0050
    BACKGROUND_YELLOW = 0x0060
    BACKGROUND_GREY = 0x0070
    BACKGROUND_INTENSITY = 0x0080  # background color is intensified.

    DEFAULT = FOREGROUND_WHITE
    CRITICAL = (
        BACKGROUND_YELLOW | FOREGROUND_RED | FOREGROUND_INTENSITY | BACKGROUND_INTENSITY
    )
    ERROR = FOREGROUND_RED | FOREGROUND_INTENSITY
    WARNING = FOREGROUND_YELLOW | FOREGROUND_INTENSITY
    INFO = FOREGROUND_GREEN
    DEBUG = FOREGROUND_CYAN

    @classmethod
    def _get_color(cls, level: int) -> str:
        """
        Define which color to print for each log level.

        Parameters
        ----------
        level: int
            The log level.

        Returns
        -------
        str
            The color to print.
        """
        if level >= logging.CRITICAL:
            return cls.CRITICAL
        elif level >= logging.ERROR:
            return cls.ERROR
        elif level >= logging.WARNING:
            return cls.WARNING
        elif level >= logging.INFO:
            return cls.INFO
        elif level >= logging.DEBUG:
            return cls.DEBUG
        else:
            return cls.DEFAULT

    def _set_color(self, code) -> None:
        import ctypes

        ctypes.windll.kernel32.SetConsoleTextAttribute(self._outhdl, code)

    def __init__(self, stream=None):
        logging.StreamHandler.__init__(self, stream)
        # get file handle for the stream
        import ctypes
        import ctypes.util

        # for some reason find_msvcrt() sometimes doesn't find msvcrt.dll on
        # my system?
        crtname = ctypes.util.find_msvcrt()
        if not crtname:
            crtname = ctypes.util.find_library("msvcrt")
        crtlib = ctypes.cdll.LoadLibrary(crtname)
        self._outhdl = crtlib._get_osfhandle(self.stream.fileno())

    def emit(self, record: logging.LogRecord) -> None:
        """
        Write a log record to the stream.

        Parameters
        ----------
        record: logging.LogRecord
            The log record to write.
        """
        color = self._get_color(record.levelno)
        self._set_color(color)
        logging.StreamHandler.emit(self, record)
        self._set_color(self.FOREGROUND_WHITE)


# select ColorStreamHandler based on platform
if platform.system() == "Windows":
    ColorStreamHandler = _WinColorStreamHandler
else:
    ColorStreamHandler = _AnsiColorStreamHandler
