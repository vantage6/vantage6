import logging

from flask import g, request
from flask_restful import Api
from http import HTTPStatus
from vantage6.common import logger_name
from vantage6.algorithm.store.resource.schema.input_schema import (
    Vantage6ServerInputSchema,
)
from vantage6.algorithm.store.resource.schema.output_schema import (
    Vantage6ServerOutputSchema,
)
from vantage6.algorithm.store.model.vantage6_server import (
    Vantage6Server as db_Vantage6Server,
)
from vantage6.algorithm.store.resource import with_authentication

# TODO move to common / refactor
from vantage6.algorithm.store.resource import AlgorithmStoreResources


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the version resource.

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
        Vantage6Servers,
        api_base + "/vantage6-server",
        endpoint="server_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )

    api.add_resource(
        Vantage6Server,
        api_base + "/vantage6-server/<int:id>",
        endpoint="server_with_id",
        methods=("GET", "DELETE"),
        resource_class_kwargs=services,
    )


v6_server_input_schema = Vantage6ServerInputSchema()
v6_server_output_schema = Vantage6ServerOutputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Vantage6Servers(AlgorithmStoreResources):
    """Resource for /algorithm"""

    @with_authentication()
    def get(self):
        """List whitelisted vantage6 servers
        ---
        description: Return a list of vantage6 servers that are whitelisted
          in this algorithm store instance.

        parameters:
          - in: query
            name: url
            schema:
              type: string
            description: Filter on algorithm name using the SQL operator LIKE.

        responses:
          200:
            description: OK
          400:
            description: Invalid input
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Vantage6 Server"]
        """
        # TODO add pagination
        # TODO extend filtering
        args = request.args
        q = g.session.query(db_Vantage6Server)

        if "url" in args:
            q = q.filter(db_Vantage6Server.url.like(args["url"]))

        servers = q.all()
        return v6_server_output_schema.dump(servers, many=True), HTTPStatus.OK

    # Note: this endpoint is not authenticated, because it is used by the
    # vantage6 server to whitelist itself.
    def post(self):
        """Create new whitelisted vantage6 server
        ---
        description: >-
          Whitelist a new vantage6 server in this algorithm store instance.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  url:
                    type: string
                    description: URL of the vantage6 server
                  force:
                    type: boolean
                    description: Force creation of the vantage6 server. If a

        responses:
          201:
            description: Algorithm created successfully
          400:
            description: Invalid input
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Vantage6 Server"]
        """
        data = request.get_json()

        # validate the request body
        errors = v6_server_input_schema.validate(data)
        if errors:
            return {
                "msg": "Request body is incorrect",
                "errors": errors,
            }, HTTPStatus.BAD_REQUEST

        # issue a warning if someone tries to whitelist localhost
        force = data.get("force", False)
        # TODO make function in common to test for localhost
        if not force and ("localhost" in data["url"] or "127.0.0.1" in data["url"]):
            return {
                "msg": "You are trying to whitelist a localhost address for a "
                "vantage6 server. This is not secure and should only be "
                "done for development servers. If you are sure you want to "
                "whitelist localhost, please specify the 'force' parameter in"
                " the request body."
            }, HTTPStatus.BAD_REQUEST

        # delete any existing record with the same url to prevent duplicates
        existing_server = db_Vantage6Server.get_by_url(data["url"])
        if existing_server:
            existing_server.delete()

        # create the whitelisted server record
        server = db_Vantage6Server(url=data["url"])
        server.save()

        return v6_server_output_schema.dump(server, many=False), HTTPStatus.CREATED


class Vantage6Server(AlgorithmStoreResources):
    """Resource for /algorithm/<id>"""

    @with_authentication()
    def get(self, id):
        """Get specific whitelisted vantage6 server
        ---
        description: Return an vantage6 server specified by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: ID of the algorithm

        responses:
          200:
            description: OK
          401:
            description: Unauthorized
          404:
            description: Algorithm not found

        security:
          - bearerAuth: []

        tags: ["Vantage6 Server"]
        """
        server = db_Vantage6Server.get(id)
        if not server:
            return {"msg": "Vantage6 server not found"}, HTTPStatus.NOT_FOUND

        return v6_server_output_schema.dump(server, many=False), HTTPStatus.OK

    @with_authentication()
    def delete(self, id):
        """Delete whitelist vantage6 server
        ---
        description: Delete a whitelisted vantage6 server specified by ID.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: ID of the algorithm

        responses:
          200:
            description: OK
          401:
            description: Unauthorized
          404:
            description: Algorithm not found

        security:
          - bearerAuth: []

        tags: ["Vantage6 Server"]
        """
        server = db_Vantage6Server.get(id)
        if not server:
            return {"msg": "Vantage6 server not found"}, HTTPStatus.NOT_FOUND

        url = server.url
        server.delete()

        return {"msg": f"Server '{url}' was successfully deleted"}, HTTPStatus.OK
