"""
WSGI (Web Server Gateway Interface) file for PyTaskManager.
"""
import pytaskmanager as ptm


import logging
logging.getLogger("urllib3").setLevel(logging.WARNING)


# Load configuration and initialize logging system
ctx = ptm.util.AppContext(ptm.APPNAME, 'server', 'default')
ctx.init(ctx.config_file, 'prod')

# Load the flask.Resources
ptm.server.init_resources(ctx)


uri = ctx.get_database_location()
ptm.server.db.init(uri)

application = ptm.server.app