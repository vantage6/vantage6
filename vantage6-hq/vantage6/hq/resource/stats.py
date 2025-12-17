# import logging

# from vantage6.server.resource import only_for
# from vantage6.server.resource._schema import CollaborationSchemaSimple
# from http import HTTPStatus

# from vantage6.common import logger_name
# from vantage6.server import db
# from vantage6.server.resource import ServicesResources


# module_name = logger_name(__name__)
# log = logging.getLogger(module_name)


# def setup(api, api_base, services):
#     path = "/".join([api_base, module_name])
#     log.info(f'Setting up "{path}" and subdirectories')

#     api.add_resource(
#         Stats,
#         path,
#         endpoint='stats',
#         methods=('GET', ),
#         resource_class_kwargs=services
#     )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
# class Stats(ServicesResources):
#     """Resource for /api/stats"""

#     # stats_schema = StatsSchema()
#     @only_for(("user", "node"))
#     def get(self, id=None):
#         schema = CollaborationSchemaSimple(many=True)

#         return {
#             'collaborations': schema.dump(db.Collaboration.get())
#         }, HTTPStatus.OK
