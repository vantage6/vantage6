import logging

from http import HTTPStatus
from flask import request, g
from flask_restful import Api
from sqlalchemy import or_, select
from marshmallow import ValidationError

from vantage6.server import db
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.backend.common import get_server_url
from vantage6.server.resource.common.input_schema import AlgorithmStoreInputSchema
from vantage6.server.permission import RuleCollection, Operation as P
from vantage6.server.resource.common.output_schema import AlgorithmStoreSchema
from vantage6.server.resource import with_user, with_user_or_node, ServicesResources
from vantage6.server.algo_store_communication import (
    post_algorithm_store,
    request_algo_store,
)


module_name = __name__.split(".")[-1]
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
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        AlgorithmStores,
        api_base + "/algorithmstore",
        endpoint="algorithm_store_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        AlgorithmStore,
        api_base + "/algorithmstore/<int:id>",
        endpoint="algorithm_store_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )


algorithm_store_schema = AlgorithmStoreSchema()
algorithm_store_input_schema = AlgorithmStoreInputSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class AlgorithmStoreBase(ServicesResources):
    """Base class for algorithm store resources."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r_col: RuleCollection = getattr(self.permissions, "collaboration")

    @staticmethod
    def get_authorization_headers_from_request() -> dict:
        """
        Get the authorization headers from the request.

        Returns
        -------
        dict
            The authorization headers
        """
        current_headers = request.headers
        if "Authorization" in current_headers:
            return {"Authorization": current_headers["Authorization"]}
        return {}


class AlgorithmStores(AlgorithmStoreBase):
    """Resource for /algorithm"""

    @with_user
    def get(self):
        """Returns a list of available algorithm stores
        ---
        description: >-
          Returns a list of available algorithm stores. Depending on your
          permission, all algorithm stores are shown or only algorithm stores
          in which your organization participates.\n\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All algorithm stores|\n
          |Collaboration|Organization|View|❌|❌|Algorithm stores within
          collaborations in which your organization participates|\n\n

          Accessible to users.

        parameters:
          - in: query
            name: name
            schema:
              type: string
            description: >-
              Name to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: url
            schema:
              type: string
            description: >-
              Algorithm store URL to match with a LIKE operator. \n
              * The percent sign (%) represents zero, one, or multiple
              characters\n
              * underscore sign (_) represents one, single character
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Collaboration id
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination (default=1)
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page (default=10)
          - in: query
            name: sort
            schema:
              type: string
            description: >-
              Sort by one or more fields, separated by a comma. Use a minus
              sign (-) in front of the field to sort in descending order.

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          400:
            description: Improper values for pagination or sorting parameters
          404:
            description: Collaboration with specified id is not found

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        # TODO make an option to GET algorithm stores that are available to all
        # collaborations

        # obtain organization from authenticated
        auth_org = self.obtain_auth_organization()
        q = select(db.AlgorithmStore)
        args = request.args

        # filter by a field of this endpoint
        for param in ["name", "url"]:
            if param in args:
                q = q.filter(getattr(db.AlgorithmStore, param).like(args[param]))

        if "collaboration_id" in args:
            collab = db.Collaboration.get(args["collaboration_id"])
            if not collab:
                return {"msg": "Collaboration not found"}, HTTPStatus.NOT_FOUND
            # TODO generalize this check (make it available as part of the
            # permission class)
            if not self.r_col.v_glo.can():
                orgs_in_collab = [org.id for org in collab.organizations]
                if not (self.r_col.v_org.can() and auth_org.id in orgs_in_collab):
                    return {
                        "msg": "You lack the permission to do that!"
                    }, HTTPStatus.UNAUTHORIZED
            q = q.filter(
                or_(
                    db.AlgorithmStore.collaboration_id == args["collaboration_id"],
                    db.AlgorithmStore.collaboration_id.is_(None),
                )
            )

        # filter based on permissions
        if not self.r_col.v_glo.can():
            collab_ids = [c.id for c in auth_org.collaborations]
            if self.r_col.v_org.can():
                q = q.filter(
                    or_(
                        db.AlgorithmStore.collaboration_id.in_(collab_ids),
                        db.AlgorithmStore.collaboration_id.is_(None),
                    )
                )
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate the results
        try:
            page = Pagination.from_query(q, request, db.AlgorithmStore)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # serialize models
        return self.response(page, algorithm_store_schema)

    @with_user
    def post(self):
        """Add algorithm store to a collaboration
        ---
        description: >-
          Register an algorithm store to a collaboration. Its algorithms will
          be available for that collaboration from then on.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to Node|Assigned to
          Container|Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Add algorithm store to a
          collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Add algorithm store to a
          collaboration that your organization is a member of|\n\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable name for the algorithm store
                  algorithm_store_url:
                    type: string
                    description: URL to the algorithm store, including the API path
                  server_url:
                    type: string
                    description: URL to this vantage6 server. This is used to
                      whitelist this server at the algorithm store. Note that
                      this is ignored if the server configuration contains
                      the 'server_url' key.
                  collaboration_id:
                    type: integer
                    description: Collaboration id to which the algorithm store
                      will be added. If not given, the algorithm store will be
                      available to all collaborations.
                  force:
                    type: boolean
                    description: Force adding the algorithm store to the
                      collaboration. This will overwrite warnings if insecure
                      addresses (e.g. localhost) are added.

        responses:
          200:
            description: Ok
          400:
            description: Wrong input data, algorithm store is already
              available for the collaboration or algorithm store is unreachable
          401:
            description: Unauthorized
          404:
            description: Collaboration with specified id is not found

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        data = request.get_json(silent=True)
        # validate request body
        try:
            data = algorithm_store_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check if collaboration exists
        collaboration_id = data.get("collaboration_id", None)
        if collaboration_id:
            collaboration_id = int(collaboration_id)
            collaboration = db.Collaboration.get(collaboration_id)
            if not collaboration:
                return {"msg": "Collaboration not found"}, HTTPStatus.NOT_FOUND

        # check permissions
        if not collaboration_id and not self.r_col.e_glo.can():
            return {
                "msg": "You lack the permission to add algorithm stores "
                "for all collaborations!"
            }, HTTPStatus.UNAUTHORIZED
        elif not self.r_col.can_for_col(P.EDIT, collaboration_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        response, status = post_algorithm_store(
            request.get_json(),
            self.config,
            headers=self.get_authorization_headers_from_request(),
        )
        if status != HTTPStatus.CREATED:
            return response, status
        else:
            return algorithm_store_schema.dump(response), status


class AlgorithmStore(AlgorithmStoreBase):
    """Resource for /algorithm/<id>"""

    @with_user_or_node
    def get(self, id):
        """Get algorithm store record
        ---
        description: >-
          Returns a specific algorithm store record.\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All algorithm stores|\n
          |Collaboration|Organization|View|❌|❌|Algorithm stores of
          collaborations in which your organization participates|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Collaboration id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        algorithm_store = db.AlgorithmStore.get(id)

        # check that collaboration exists, unlikely to happen without ID
        if not algorithm_store:
            return {"msg": f"Algorithm store id={id} not found"}, HTTPStatus.NOT_FOUND

        # verify that the user organization is within the collaboration
        # algorithm stores that are available to all collaborations are
        # always visible
        if not self.r_col.v_glo.can():
            auth_org_id = self.obtain_organization_id()
            ids = []
            if algorithm_store.collaboration:
                ids = [org.id for org in algorithm_store.collaboration.organizations]
            if not (
                self.r_col.v_org.can()
                and (auth_org_id in ids or not algorithm_store.collaboration_id)
            ):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        return (
            algorithm_store_schema.dump(algorithm_store, many=False),
            HTTPStatus.OK,
        )  # 200

    # Note that this endpoint cannot be used to change the collaboration_id
    # or the url of the algorithm store, because those actions make little
    # sense and/or require additional checks. Users should then delete the
    # algorithm store link and create a new one.
    @with_user
    def patch(self, id):
        """Update algorithm store record

        Note that the algorithm store's URL cannot be changed, because it cannot be
        checked if the new URL represents the same algorithm store as the old URL. In
        such cases, please delete and re-add the algorithm store link.

        ---
        description: >-
          Updates the linked algorithm store with the specified id. Note that
          you cannot change the collaboration or the algorithm store URL: these
          can only be modified by deleting and re-creating the algorithm store
          link.\n\n
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Update any algorithm store|\n
          |Collaboration|Collaboration|Edit|❌|❌|Update algorithm stores
          within a collaboration that your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Algorithm store id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable label
                  collaboration_id:
                    type: integer
                    description: Collaboration id to which the algorithm store
                      will be added. If set to None, the algorithm store will
                      be available to all collaborations.

        responses:
          200:
            description: Ok
          400:
            description: Wrong input data
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        algorithm_store = db.AlgorithmStore.get(id)
        # check if collaboration exists
        if not algorithm_store:
            return {
                "msg": f"Algorithm store with id={id} can not be found"
            }, HTTPStatus.NOT_FOUND  # 404

        # validate request body
        data = request.get_json(silent=True)
        try:
            data = algorithm_store_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # verify permissions - check permission for old collaboration
        collaboration_id_old = algorithm_store.collaboration_id
        if not self.r_col.can_for_col(P.EDIT, collaboration_id_old):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # verify permissions - check permission for new collaboration (if
        # specified) AND the old one
        data = request.get_json()
        if "collaboration_id" in data:
            collaboration_id_new = data["collaboration_id"]
            if not self.r_col.can_for_col(
                P.EDIT, collaboration_id_new
            ) or not self.r_col.can_for_col(P.EDIT, collaboration_id_old):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # only update fields that are provided
        name = data.get("name")
        if name is not None:
            algorithm_store.name = name

        # update collaboration_id if specified - also if it is set to None (
        # that makes it available to all collaborations)
        if "collaboration_id" in data:
            algorithm_store.collaboration_id = data["collaboration_id"]

        algorithm_store.save()

        return (
            algorithm_store_schema.dump(algorithm_store, many=False),
            HTTPStatus.OK,
        )  # 200

    @with_user
    def delete(self, id):
        """Delete linked algorithm store record
        ---
        description: >-
          Removes the algorithm store from the database entirely.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Remove any algorithm store from any
          collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Remove any algorithm store
          from a collaboration that your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Algorithm store id
            required: true
          - in: query
            name: server_url
            schema:
              type: string
            description: URL to this vantage6 server. This is used to delete
              the whitelisting of this server at the algorithm store. Note that
              this is ignored if the server configuration contains the
              'server_url' key.

        responses:
          200:
            description: Ok
          404:
            description: Algorithm store with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        algorithm_store = db.AlgorithmStore.get(id)
        if not algorithm_store:
            return {
                "msg": f"Algorithm store id={id} is not found"
            }, HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r_col.can_for_col(P.EDIT, algorithm_store.collaboration_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # Check if algostore is used by other collaborations. If it is, user needs
        # to have global permissions to delete all those links.
        # TODO require extra --force parameter to do this?
        all_stores_with_url = db.AlgorithmStore.get_by_url(algorithm_store.url)
        if len(all_stores_with_url) > 1:
            if self.r_col.e_glo.can():
                log.warning(
                    "Deleting algorithm store with id=%s, which is also used by"
                    " other collaborations",
                    id,
                )
            else:
                return {
                    "msg": "This algorithm store is used by other collaborations. "
                    "You lack the permission to delete it!"
                }, HTTPStatus.UNAUTHORIZED

        # only this algorithm store uses this url, so delete the
        # whitelisting
        server_url = get_server_url(self.config, request.args.get("server_url"))
        if not server_url:
            return {
                "msg": "The 'server_url' query parameter is required"
            }, HTTPStatus.BAD_REQUEST

        # get the ID of the whitelisted server, then delete it
        response, status = request_algo_store(
            algorithm_store.url,
            server_url,
            endpoint="vantage6-server",
            method="get",
            headers=self.get_authorization_headers_from_request(),
        )
        if status == HTTPStatus.FORBIDDEN:
            log.info(
                "Server with url=%s was not whitelisted at the algorithm store. "
                "Proceeding to remove algorithm store store from server...",
                server_url,
            )
            # initialize empty list of servers to delete at store
            result = []
        elif status != HTTPStatus.OK:
            return response, status
        else:
            result = response.json()
            if len(result) > 1:
                msg = (
                    "More than one whitelisted server found with url "
                    f"{server_url}. This should not happen! All will be "
                    "removed."
                )
                log.warning(msg)
            elif len(result) == 0:
                msg = (
                    "No whitelisted server found with url "
                    f"{server_url}. This should not happen!"
                )
                log.warning(msg)
        # remove all linked servers with the given url
        for server in result:
            server_id = server["id"]
            response, status = request_algo_store(
                algorithm_store.url,
                server_url,
                endpoint=f"vantage6-server/{server_id}",
                method="delete",
                headers=self.get_authorization_headers_from_request(),
            )
            if status != HTTPStatus.OK:
                return response, status

        # remove the store link from all tasks linked to this store
        for task in algorithm_store.tasks:
            task.store = None
            task.save()

        # finally delete the algorithm store record itself
        # pylint: disable=expression-not-assigned
        [store.delete() for store in all_stores_with_url]
        return {"msg": f"Algorithm store id={id} successfully deleted"}, HTTPStatus.OK
