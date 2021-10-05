# -*- coding: utf-8 -*-
import logging

from flask.globals import g
from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path
from sqlalchemy.exc import InvalidRequestError

from vantage6.server.resource import ServicesResources
from vantage6.common import logger_name
from vantage6.server.model.base import Database


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Health,
        path,
        endpoint='health',
        methods=('GET',),
        resource_class_kwargs=services
    )

    api.add_resource(
        Fix,
        path + "/fix",
        methods=('GET',),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Health(ServicesResources):

    @swag_from(str(Path(r"swagger/get_health.yaml")), endpoint='health')
    def get(self):
        """displays the health of services"""

        # test DB
        db_ok = False
        try:
            g.session.execute('SELECT 1')
            db_ok = True
        except Exception as e:
            log.error("DB not responding")
            log.debug(e)

        return {'database': db_ok}, HTTPStatus.OK


class Fix(ServicesResources):

    def get(self):
        """Experimental switch to fix db errors"""

        try:
            g.session.execute('SELECT 1')
        except (InvalidRequestError, Exception) as e:
            log.error("DB FIX IS NOT IMPLEMENTED ANYMORE")
            log.debug(e)
