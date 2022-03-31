import sys

from vantage6.common import error
from vantage6.server import run_server

if len(sys.argv) < 2:
    error("No config file provided from WSGI! Exiting...")
    exit(1)
config_file = sys.argv[1]

server_app = run_server(config_file, system_folders=False)
app = server_app.app
