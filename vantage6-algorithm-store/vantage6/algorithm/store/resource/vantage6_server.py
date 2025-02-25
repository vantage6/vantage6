import logging

from http import HTTPStatus
from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from http import HTTPStatus
from sqlalchemy import select

from vantage6.common import logger_name
from vantage6.algorithm.store.permission import PermissionManager, Operation as P
from vantage6.algorithm.store.resource.schema.input_schema import (
    Vantage6ServerInputSchema,
)
from vantage6.algorithm.store.resource.schema.output_schema import (
    Vantage6ServerOutputSchema,
)
from vantage6.algorithm.store.model.vantage6_server import (
    Vantage6Server as db_Vantage6Server,
)
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.resource import (
    request_validate_server_token,
    with_authentication,
    with_permission,
)

# TODO move to common / refactor
from vantage6.algorithm.store.resource import AlgorithmStoreResources
from vantage6.algorithm.store.default_roles import DefaultRole


module_name = __name__.split(".")[-1]
log = logging.getLogger(logger_name(__name__))


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


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """

    log.debug("Loading module vantage6_server permission")
    add = permissions.appender(module_name)
    add(P.DELETE, description="Delete your own whitelisted vantage6 server")


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
        q = select(db_Vantage6Server)

        if "url" in args:
            q = q.filter(db_Vantage6Server.url.like(args["url"]))

        servers = g.session.scalars(q).all()
        return v6_server_output_schema.dump(servers, many=True), HTTPStatus.OK

    # Note: this endpoint is not authenticated, because it is used by the
    # vantage6 server to whitelist itself. It is protected by policies of the store
    # itself, which can define if a server is allowed to be whitelisted.
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
                    description: Force creation of the vantage6 server. This argument is
                      required to whitelist localhost addresses.


        responses:
          201:
            description: Algorithm created successfully
          400:
            description: Invalid input
          403:
            description: Forbidden by algorithm store policies

        security:
          - bearerAuth: []

        tags: ["Vantage6 Server"]
        """
        data = request.get_json(silent=True)

        # validate the request body
        try:
            data = v6_server_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # Check with the policies if the server is allowed to be whitelisted
        allowed_servers = Policy.get_servers_allowed_to_be_whitelisted()
        if allowed_servers and data["url"] not in allowed_servers:
            return {
                "msg": "This server is not allowed to be whitelisted by the "
                "administrator of this algorithm store instance."
            }, HTTPStatus.FORBIDDEN

        # issue a warning if someone tries to whitelist localhost
        force = data.get("force", False)
        # TODO make function in common to test for localhost
        if "localhost" in data["url"] or "127.0.0.1" in data["url"]:
            if not Policy.is_localhost_allowed_to_be_whitelisted():
                return {
                    "msg": "Whitelisting localhost is not allowed by the "
                    "administrator of this algorithm store instance."
                }, HTTPStatus.FORBIDDEN
            elif not force:
                return {
                    "msg": "You are trying to whitelist a localhost address for a "
                    "vantage6 server. This is not secure and should only be "
                    "done for development servers. If you are sure you want to "
                    "whitelist localhost, please specify the 'force' parameter in"
                    " the request body."
                }, HTTPStatus.BAD_REQUEST
            # else log warning
            log.warning(
                "Whitelisting localhost for vantage6 server. This is not "
                "recommended for production environments."
            )

        # users can only whitelist their own server. Check if this is the case
        user_validate_response, status_code = request_validate_server_token(data["url"])
        if user_validate_response is None or status_code != HTTPStatus.OK:
            return {
                "msg": "You can only whitelist your own vantage6 server! It could not "
                "be verified that you are from the server you are trying to whitelist."
            }, HTTPStatus.FORBIDDEN

        # only create a new server if previous didn't exist yet
        existing_server = db_Vantage6Server.get_by_url(data["url"])
        if not existing_server:
            # create the whitelisted server record
            server = db_Vantage6Server(url=data["url"])
            server.save()
        else:
            return {
                "msg": "This server is already whitelisted in this algorithm store "
                "instance."
            }, HTTPStatus.ALREADY_REPORTED

        # the user that is whitelisting the server should be able to delete it
        # in the future. Assign the server manager role to the user executing this
        # request.
        username = user_validate_response.json()["username"]
        email = user_validate_response.json()["email"]
        organization_id = user_validate_response.json()["organization_id"]
        self._assign_server_manager_role_to_auth_user(
            server, username, email, organization_id
        )

        return v6_server_output_schema.dump(server, many=False), HTTPStatus.CREATED

    def _assign_server_manager_role_to_auth_user(
        self, server: db_Vantage6Server, username: str, email: str, organization_id: int
    ) -> None:
        """
        Assign the server manager role to the user that is currently authenticated.

        Parameters
        ----------
        server : db.Vantage6Server
            The server that is being whitelisted
        username : str
            The username of the user that is whitelisting the server
        email : str
            The email of the user that is whitelisting the server
        organization_id : int
            The organization id of the user that is whitelisting the server
        """
        # then find if the user already exists
        user = User.get_by_server(username, server.id)
        server_manager_role = Role.get_by_name(DefaultRole.SERVER_MANAGER)
        if not user:
            # create new user registration
            user = User(
                username=username,
                email=email,
                organization_id=organization_id,
                v6_server_id=server.id,
                roles=[server_manager_role],
            )
            user.save()
        else:
            # check if the user already has the server manager role or all of its rules
            server_manager_rules = server_manager_role.rules
            user_rules = [rule for role in user.roles for rule in role.rules]
            if not all(rule in user_rules for rule in server_manager_rules):
                # update existing user registration
                user.roles.append(server_manager_role)
                user.save()


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

    @with_permission(module_name, P.DELETE)
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

        # verify that the server they are trying to delete is their own. Note that the
        # @with_permission decorator already checks that the user sending the request
        # is indeed authenticated at this server URL.
        own_server_url = request.headers["Server-Url"]
        url = server.url
        if url != own_server_url:
            return {
                "msg": "You can only delete your own whitelisted vantage6 server"
            }, HTTPStatus.FORBIDDEN

        # delete server and its linked users
        # pylint: disable=expression-not-assigned
        [user.delete() for user in server.users]
        server.delete()

        return {"msg": f"Server '{url}' was successfully deleted"}, HTTPStatus.OK
