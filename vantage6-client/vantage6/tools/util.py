import sys


def info(msg: str):
    sys.stdout.write(f"info > {msg}\n")


def warn(msg: str):
    sys.stdout.write(f"warn > {msg}\n")


def error(msg: str):
    sys.stdout.write(f"error > {msg}\n")
