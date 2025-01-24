"""
This is the WSGI entry-point for the vantage6 server. When the
server is started using the `v6 server start` command, it is started from here.
"""

# TODO this has been added to __init__ to raise errors for sqlalchemy deprecations
# Should be removed when all deprecations are fixed
import warnings
from sqlalchemy import exc

warnings.filterwarnings("ignore", category=DeprecationWarning)

# Enable SQLAlchemy deprecation warnings
warnings.filterwarnings("error", category=exc.RemovedIn20Warning)

import sys

from vantage6.common import error
from vantage6.algorithm.store import run_server

if len(sys.argv) < 2:
    error("No config file provided from WSGI! Exiting...")
    exit(1)
config_file = sys.argv[1]

server_app = run_server(config_file, system_folders=False)
app = server_app.app
