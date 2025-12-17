"""
This is the WSGI entry-point for the vantage6 algorithm store. When the
store is started using the `v6 algorithm-store start` command, it is started from here.
"""

import sys

from vantage6.common import error

from vantage6.algorithm.store import run_store

if len(sys.argv) < 2:
    error("No config file provided from WSGI! Exiting...")
    exit(1)
config_file = sys.argv[1]

store_app = run_store(config_file, system_folders=False)
app = store_app.app
