"""
WSGI (Web Server Gateway Interface) file for PyTaskManager.
"""
import os
import mod_wsgi

import pytaskmanager as ptm
import pytaskmanager.server

# import logging
# logging.getLogger("urllib3").setLevel(logging.WARNING)


# # Load configuration and initialize logging system
# ctx = ptm.util.ServerContext(ptm.APPNAME, 'default')
# ctx.init(ctx.config_file, 'prod')

# # Load the flask.Resources
# ptm.server.init_resources(ctx)


# uri = ctx.get_database_location()
# ptm.server.db.init(uri)
env = mod_wsgi.application_group
if env not in ['dev', 'test', 'acc', 'prod']:
    env = 'prod'


print('-' * 80)
print('Using environment: {}'.format(env))
print('-' * 80)
ptm.server.init(env, init_resources=True)

application = ptm.server.app
