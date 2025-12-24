"""
This is the WSGI entry-point for the vantage6 HQ. When HQ is started using the
`v6 hq start` command, it is started from here.
"""

import sys

from vantage6.common import error

from vantage6.hq import run_hq

if len(sys.argv) < 2:
    error("No config file provided from WSGI! Exiting...")
    exit(1)
config_file = sys.argv[1]

hq_app = run_hq(config_file, system_folders=False)
app = hq_app.app
