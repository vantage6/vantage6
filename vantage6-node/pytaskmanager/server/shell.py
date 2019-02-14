import sys

from pytaskmanager.server import db, APPNAME
from pytaskmanager import util
from pytaskmanager.util.find_files import get_config_location

from sqlalchemy.engine.url import make_url

environment = sys.argv[1]

ctx = util.AppContext(
    application=APPNAME, 
    instance_type='server', 
    instance_name='default'
)

cfg_filename = get_config_location(ctx, None, force_create=False)
ctx.init(cfg_filename, environment, setup_logging=False)

# initialize database from environment
uri = ctx.get_database_location()
url = make_url(uri)

print()
print("Initializing the database")
print("  driver:   {}".format(url.drivername))
print("  host:     {}".format(url.host))
print("  port:     {}".format(url.port))
print("  database: {}".format(url.database))
print("  username: {}".format(url.username))

db.init(uri)
