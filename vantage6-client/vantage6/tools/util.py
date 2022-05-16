import sys


def info(msg):
    sys.stdout.write("info > "+msg+"\n")


def warn(msg):
    sys.stdout.write("warn > "+msg+"\n")


def error(msg):
    sys.stdout.write("error > "+msg+"\n")
