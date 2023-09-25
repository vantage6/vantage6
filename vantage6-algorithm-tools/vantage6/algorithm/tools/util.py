import sys


def info(msg: str) -> None:
    """
    Print an info message to stdout.

    Parameters
    ----------
    msg : str
        Message to be printed
    """
    sys.stdout.write(f"info > {msg}\n")


def warn(msg: str) -> None:
    """
    Print a warning message to stdout.

    Parameters
    ----------
    msg : str
        Warning message to be printed
    """
    sys.stdout.write(f"warn > {msg}\n")


def error(msg: str) -> None:
    """
    Print an error message to stdout.

    Parameters
    ----------
    msg : str
        Error message to be printed
    """
    sys.stdout.write(f"error > {msg}\n")
