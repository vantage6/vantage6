import logging

from http import HTTPStatus
from flask.globals import g
from flask_restful import Api

from vantage6.server.resource import ServicesResources
from vantage6.common import logger_name


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the health resource.

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
        Health,
        path,
        endpoint="health",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Health(ServicesResources):
    def get(self):
        """Displays the health of services
        ---
        description: >-
          Checks if server can communicate with the database. If not, it throws
          an exception.

        responses:
          200:
            description: Ok

        security:
        - bearerAuth: []

        tags: ["Database"]
        """

        # test DB
        db_ok = False
        try:
            g.session.execute("SELECT 1")
            db_ok = True
        except Exception as e:
            log.error("DB not responding")
            log.exception(e)

        return {"database": db_ok}, HTTPStatus.OK
