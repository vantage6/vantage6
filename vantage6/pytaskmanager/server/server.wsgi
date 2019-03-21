"""
WSGI (Web Server Gateway Interface) file for PyTaskManager.
"""
import os
# import mod_wsgi

import pytaskmanager as ptm
import pytaskmanager.server
from pytaskmanager.server import db
import pytaskmanager.util as util
from pytaskmanager.constants import APPNAME
from pytaskmanager.util.context import get_config_location


#FIXME: this is a temporary solution to proof uWSGI works ... 
env = 'test'
name = 'default'
ctx = util.AppContext(APPNAME, 'server', name)

# load configuration and initialize logging system
cfg_filename = get_config_location(ctx, None, force_create=False)
ctx.init(cfg_filename, env)

# initialize database from environment
db.init(ctx.get_database_location())
ptm.server.init_resources(ctx)
application = ptm.server.app
