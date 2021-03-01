# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/version'
"""
import logging

from flasgger import swag_from
from pathlib import Path
from http import HTTPStatus
from vantage6.common import logger_name
from vantage6.server.resource import ServicesResources
from vantage6.server._version import __version__


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Version,
        path,
        endpoint='version',
        methods=('GET',),
        resource_class_kwargs=services
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Version(ServicesResources):

    @swag_from(str(Path(r"swagger/get_version.yaml")), endpoint='version')
    def get(self):
        """Return the version of this server."""

        return {"version": __version__}, HTTPStatus.OK
