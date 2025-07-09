"""
Resource to get details on the server configuration from the UI.
"""

from http import HTTPStatus

import logging
from flask_restful import Api

from vantage6.common import logger_name
from vantage6.server.resource import ServicesResources, with_user


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the column resource.

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
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        KeycloakConfigSettings,
        path + "/keycloak",
        endpoint="keycloak_config_settings",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


class KeycloakConfigSettings(ServicesResources):
    """Resource for getting the keycloak config settings."""

    @with_user
    def get(self):
        """Get the keycloak config settings. This is used in the user interface to
        determine whether e.g. the user has to provide a password when creating a user.
        ---
        description: >-
          Returns config option whether users and nodes should be created in keycloak
          by the server.

          Any authenticated user can access this endpoint.

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Authentication"]
        """
        return {
            "manage_users_and_nodes": self.config.get("keycloak", {}).get(
                "manage_users_and_nodes", True
            )
        }, HTTPStatus.OK
