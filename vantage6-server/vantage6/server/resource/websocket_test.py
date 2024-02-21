import logging

from http import HTTPStatus
from flask_restful import Api

from vantage6.common import logger_name
from vantage6.server.resource import ServicesResources


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the collaboration resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Test, path, endpoint="test", methods=("GET",), resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Test(ServicesResources):
    def get(self):
        """Web socket test
        ---
        description: >-
          Returns a response to check that the websocket works as intended.

        responses:
          200:
            description: Ok

        tags: ["Other"]
        """
        self.socketio.send("you're welcome!", room="all_nodes")
        return self.socketio.server.manager.rooms, HTTPStatus.OK
