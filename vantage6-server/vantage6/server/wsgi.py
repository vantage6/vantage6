"""
This is the WSGI entry-point for the vantage6 server. When the
server is started using the `v6 server start` command, it is started from here.
"""

import os

from vantage6.common import error

from vantage6.server import run_server

config_file = os.getenv("VANTAGE6_CONFIG_LOCATION")
if not config_file:
    error("No config file provided (argv or VANTAGE6_CONFIG_LOCATION). Exiting...")
    exit(1)

server_app = run_server(config_file, system_folders=False)
app = server_app.app
