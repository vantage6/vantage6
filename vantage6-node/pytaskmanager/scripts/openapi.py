from apispec import APISpec
import yaml

import apispec_flask_restful
import json

# Create spec
spec = APISpec(
    title='PyTaskManager',
    version='0.1',
    info=dict(
        description='You know, for devs'
    ),
    plugins=[
        'apispec_flask_restful'
    ]
)

# Reference your schemas definitions
#from pytaskmanager.server.resource._schema import TaskSchema

#spec.definition('Task', schema=TaskSchema)
# ...

# Now, reference your routes.
from pytaskmanager.server.resource.organization import Organization

# We need a working context for apispec introspection.
from pytaskmanager import server, util
from pytaskmanager.util import find_files

# ctx = util.AppContext('pymanagertest', 'server', 'test')
#
# # load configuration and initialize logging system
# cfg_filename = find_files.get_config_location(ctx, 'test', force_create=True)
# ctx.init(cfg_filename, 'test')
#
# app = server.run(ctx, debug=True, host='localhost', port=5000)

from pytaskmanager.server import db
from pytaskmanager.server import fixtures



db.init('sqlite://')
fixtures.create()

server.app.testing = True
ctx = util.AppContext('pymanagertest', 'server', 'default')
cfg_filename = find_files.get_config_location(ctx, 'test', force_create=False)
ctx.init(cfg_filename, 'default')
server.init_resources(ctx)

print("swagger...")

from pytaskmanager.server.resource.node import Node
import pprint
from flask_restful import Resource



#with server.app.test_request_context():

spec.add_path(resource=Node, path="/api/node/")
spec.add_path(resource=Node, path="/api/node/{id}")

print("Specification.....")
print(spec.to_yaml())

# We're good to go! Save this to a file for now.
with open('C:/Users/FMa1805.36838/swagger.yml', 'w') as f:
    yaml.dump(spec.to_dict(), f)

