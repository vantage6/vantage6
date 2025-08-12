import logging
from http import HTTPStatus

from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.backend.common.resource.pagination import Pagination

from vantage6.server import db
from vantage6.server.permission import (
    Operation as P,
    PermissionManager,
    RuleCollection,
    Scope as S,
)
from vantage6.server.resource import ServicesResources, only_for, with_user
from vantage6.server.resource.common.input_schema import (
    CollaborationAddNodeSchema,
    CollaborationChangeOrganizationSchema,
    CollaborationInputSchema,
)
from vantage6.server.resource.common.output_schema import (
    CollaborationSchema,
    CollaborationWithOrgsSchema,
    NodeSchemaSimple,
    OrganizationSchema,
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
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Collaborations,
        path,
        endpoint="collaboration_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Collaboration,
        path + "/<int:id>",
        endpoint="collaboration_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        CollaborationOrganization,
        path + "/<int:id>/organization",
        endpoint="collaboration_with_id_organization",
        methods=("POST", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        CollaborationNode,
        path + "/<int:id>/node",
        endpoint="collaboration_with_id_node",
        methods=("POST", "DELETE"),
        resource_class_kwargs=services,
    )


# Schemas
collaboration_schema = CollaborationSchema()
org_schema = OrganizationSchema()
node_schema = NodeSchemaSimple()
collaboration_input_schema = CollaborationInputSchema()
collaboration_change_org_schema = CollaborationChangeOrganizationSchema()
collaboration_add_node_schema = CollaborationAddNodeSchema()
collab_with_orgs_schema = CollaborationWithOrgsSchema()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """

    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any collaboration")

    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        assign_to_container=True,
        assign_to_node=True,
        description="view collaborations of your organization",
    )

    add(scope=S.GLOBAL, operation=P.EDIT, description="edit any collaboration")
    add(
        scope=S.COLLABORATION,
        operation=P.EDIT,
        description="edit any collaboration that your organization participates in",
    )

    add(scope=S.GLOBAL, operation=P.CREATE, description="create a new collaboration")

    add(scope=S.GLOBAL, operation=P.DELETE, description="delete a collaboration")
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete any collaboration that your organization participates in",
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class CollaborationBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    def _select_schema(self) -> CollaborationSchema:
        """
        Select the output schema based on which resources should be included

        Returns
        -------
        CollaborationSchema or derivative of it
            Schema to use for serialization
        """
        if self.is_included("organizations"):
            return collab_with_orgs_schema
        else:
            return collaboration_schema


class Collaborations(CollaborationBase):
    @only_for(("user", "node"))
    def get(self):
        """Returns a list of collaborations
        ---
        description: >-
          Returns a list of collaborations. Depending on your permission, all
          collaborations are shown or only collaborations in which your
          organization participates. See the table bellow.\n\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All collaborations|\n
          |Collaboration|Organization|View|✅|✅|Collaborations in which
          your organization participates |\n\n

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
            name: encrypted
            schema:
              type: boolean
            description: Whether or not collaboration is encrypted
          - in: query
            name: organization_id
            schema:
              type: integer
            description: Organization id
          - in: query
            name: algorithm_store_id
            schema:
              type: integer
            description: Algorithm store ID that is available to the collaboration
          - in: query
            name: include
            schema:
              type: array
              items:
                type: string
            description: Include 'organizations' to include the organizations
              within the collaboration.
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

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        # obtain organization from authenticated
        auth_org_id = self.obtain_organization_id()
        q = select(db.Collaboration)
        args = request.args

        # filter by a field of this endpoint
        if "encrypted" in args:
            q = q.filter(db.Collaboration.encrypted == args["encrypted"])
        if "name" in args:
            q = q.filter(db.Collaboration.name.like(args["name"]))

        # find collaborations containing a specific organization
        if "organization_id" in args:
            if not self.r.v_glo.can() and args["organization_id"] != str(auth_org_id):
                return {
                    "msg": "You lack the permission to request collaborations "
                    "for this organization!"
                }, HTTPStatus.UNAUTHORIZED
            elif self.r.v_glo.can():
                q = (
                    q.join(db.Member)
                    .join(db.Organization)
                    .filter(db.Organization.id == args["organization_id"])
                )
            # else: no filter if user can only view collaborations of own
            # organization: the arg 'organization_id' is then superfluous

        if "algorithm_store_id" in args:
            # If this algorithm store is available for all collaborations, no filter is
            # needed
            store = db.AlgorithmStore.get(args["algorithm_store_id"])
            if not store:
                return {
                    "msg": f"Algorithm store with id={args['algorithm_store_id']} not found"
                }, HTTPStatus.NOT_FOUND
            elif store.collaboration_id is not None:
                # filter on collaborations that have access to this algorithm store
                q = q.join(db.AlgorithmStore).filter(
                    db.AlgorithmStore.collaboration_id == db.Collaboration.id,
                )

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_org.can():
                q = q.join(db.Organization, db.Collaboration.organizations).filter(
                    db.Collaboration.organizations.any(id=auth_org_id)
                )
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate the results
        try:
            page = Pagination.from_query(q, request, db.Collaboration)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        schema = self._select_schema()

        # serialize models
        return self.response(page, schema)

    @with_user
    def post(self):
        """Create collaboration
        ---
        description: >-
          Create a new collaboration between organizations.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to Node|Assigned to
          Container|Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Create|❌|❌|Create collaboration|\n\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Unique human readable name for collaboration
                  organization_ids:
                    type: array
                    items:
                      type: integer
                      description: List of organization ids which form the
                        collaboration
                  encrypted:
                    type: integer
                    description: Boolean (0 or 1) to indicate if the
                      collaboration uses encryption
                  session_restrict_to_same_image:
                    type: integer
                    description: Boolean (0 or 1) to indicate if the session
                      should be restricted to the same image. By default set to 0.

        responses:
          200:
            description: Ok
          400:
            description: Collaboration name already exists
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        data = request.get_json(silent=True)

        try:
            data = collaboration_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        name = data["name"]
        if db.Collaboration.exists("name", name):
            return {
                "msg": f"Collaboration name '{name}' already exists!"
            }, HTTPStatus.BAD_REQUEST

        if not self.r.c_glo.can():
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        encrypted = True if data["encrypted"] == 1 else False
        restricted_sessions = (
            True if data["session_restrict_to_same_image"] == 1 else False
        )

        collaboration = db.Collaboration(
            name=name,
            organizations=[
                db.Organization.get(org_id)
                for org_id in data["organization_ids"]
                if db.Organization.get(org_id)
            ],
            encrypted=encrypted,
            session_restrict_to_same_image=restricted_sessions,
        )

        collaboration.save()
        return collaboration_schema.dump(collaboration), HTTPStatus.OK


class Collaboration(CollaborationBase):
    @only_for(("user", "node", "container"))
    def get(self, id):
        """Get collaboration
        ---
        description: >-
          Returns the collaboration with the specified id.\n

          ### Permission Table\n
          |Rulename|Scope|Operation|Assigned to Node|Assigned to Container|
          Description|\n
          | -- | -- | -- | -- | -- | -- |\n
          |Collaboration|Global|View|❌|❌|All collaborations|\n
          |Collaboration|Organization|View|✅|✅|Collaborations in which
          your organization participates |\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
              minimum: 1
            description: Collaboration id
            required: true
          - in: query
            name: include
            schema:
              type: array
              items:
                type: string
            description: Include 'organizations' to include the organizations
              within the collaboration.

        responses:
          200:
            description: Ok
          404:
            description: Collaboration with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        collaboration = db.Collaboration.get(id)

        # check that collaboration exists
        if not collaboration:
            return {
                "msg": f"collaboration having id={id} not found"
            }, HTTPStatus.NOT_FOUND

        # obtain the organization id of the authenticated
        auth_org_id = self.obtain_organization_id()

        # verify that the user/node organization is within the
        # collaboration
        ids = [org.id for org in collaboration.organizations]
        if not self.r.v_glo.can():
            if not (self.r.v_org.can() and auth_org_id in ids):
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        schema = self._select_schema()

        return schema.dump(collaboration, many=False), HTTPStatus.OK  # 200

    @with_user
    def patch(self, id):
        """Update collaboration
        ---
        description: >-
          Updates the collaboration with the specified id.\n\n
          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Update a collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Update a collaboration that
          you are already a member of|\n\n

          Accessible to users.

          Note that the session_restrict_to_same_image field is not editable. If that
          would be changed from False to True, all sessions in the collaboration would
          be invalidated. Due to these complications, the field is not editable.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Human readable label
                  organization_ids:
                    type: array
                    items:
                      type: integer
                    description: List of organization ids
                  encrypted:
                    type: boolean
                    description: Whether collaboration is encrypted or not

        responses:
          200:
            description: Ok
          404:
            description: Collaboration with specified id is not found
          401:
            description: Unauthorized
          400:
            description: Collaboration name already exists

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        collaboration = db.Collaboration.get(id)

        # check if collaboration exists
        if not collaboration:
            return {
                "msg": f"collaboration having collaboration_id={id} can not be found"
            }, HTTPStatus.NOT_FOUND  # 404

        # verify permissions
        if not self.r.can_for_col(P.EDIT, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        data = request.get_json(silent=True)
        # validate request body
        try:
            data = collaboration_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # only update fields that are provided
        if "name" in data:
            name = data["name"]
            if collaboration.name != name and db.Collaboration.exists("name", name):
                return {
                    "msg": f"Collaboration name '{name}' already exists!"
                }, HTTPStatus.BAD_REQUEST
            collaboration.name = name
        if "organization_ids" in data:
            # Users with permission to edit a collaboration at collaboration scope are
            # not allowed to change the organizations of the collaboration: that would
            # be a permission escalation as doing so may allow them to also do other
            # actions for newly added organizations. Therefore, only users with global
            # permission can alter the organizations in a collaboration.
            if not self.r.e_glo.can():
                return {
                    "msg": "You lack the permission to change the organizations of a "
                    "collaboration!"
                }, HTTPStatus.UNAUTHORIZED
            # set new organizations
            collaboration.organizations = [
                db.Organization.get(org_id)
                for org_id in data["organization_ids"]
                if db.Organization.get(org_id)
            ]
        if "encrypted" in data:
            collaboration.encrypted = data["encrypted"]

        collaboration.save()

        return (
            collaboration_schema.dump(collaboration, many=False),
            HTTPStatus.OK,
        )  # 200

    @with_user
    def delete(self, id):
        """Delete collaboration
        ---
        description: >-
          Removes the collaboration from the database entirely.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Delete|❌|❌|Remove collaboration|\n
          |Collaboration|Collaboration|Delete|❌|❌|Remove collaborations
          that you are part of yourself|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id
            required: true
          - in: query
            name: delete_dependents
            schema:
              type: boolean
            description: If set to true, the collaboratio will be deleted along
              with all its tasks and nodes (default=False)

        responses:
          200:
            description: Ok
          404:
            description: Collaboration with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """

        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration id={id} is not found"}, HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r.can_for_col(P.DELETE, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        if collaboration.tasks or collaboration.nodes or collaboration.studies:
            delete_dependents = request.args.get("delete_dependents", False)
            if not delete_dependents:
                return {
                    "msg": f"Collaboration id={id} has "
                    f"{len(collaboration.tasks)} tasks, {len(collaboration.nodes)} "
                    f"nodes and {len(collaboration.studies)} studies. Please delete "
                    "them separately or set delete_dependents=True"
                }, HTTPStatus.BAD_REQUEST
            else:
                log.warning(
                    "Deleting collaboration id=%s along with %s tasks, %s nodes and "
                    "% studies.",
                    id,
                    len(collaboration.tasks),
                    len(collaboration.nodes),
                    len(collaboration.studies),
                )
                for task in collaboration.tasks:
                    task.delete()
                for node in collaboration.nodes:
                    node.delete()
                for study in collaboration.studies:
                    study.delete()

        collaboration.delete()
        return {"msg": f"Collaboration id={id} successfully deleted"}, HTTPStatus.OK


class CollaborationOrganization(ServicesResources):
    """Resource for /api/collaboration/<int:id>/organization."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    @with_user
    def post(self, id):
        """Add organization to collaboration
        ---
        description: >-
          Adds a single organization to an existing collaboration.\n\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Add organization to a
          collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Add organization to a
          collaboration that your organization is already a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Organization id which needs to be added

        responses:
          200:
            description: Ok
          404:
            description: Specified collaboration or organization does not exist
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        # get collaboration to which te organization should be added
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {
                "msg": f"collaboration having collaboration_id={id} can not be found"
            }, HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r.can_for_col(P.EDIT, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # validate request body
        data = request.get_json(silent=True)
        try:
            data = collaboration_change_org_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # get the organization
        organization = db.Organization.get(data["id"])
        if not organization:
            return {
                "msg": f"organization with id={id} is not found"
            }, HTTPStatus.NOT_FOUND

        # append organization to the collaboration
        collaboration.organizations.append(organization)
        collaboration.save()
        return org_schema.dump(collaboration.organizations, many=True), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """Remove organization from collaboration
        ---
        description: >-
          Removes a single organization from an existing collaboration.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Remove an organization from an
          existing collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Remove an organization from
          an existing collaboration that your organization is a member of|\n\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Organization id which needs to be deleted

        responses:
          200:
            description: Ok
          404:
            description: Specified collaboration or organization does not exist
          401:
            description: Unauthorized

        tags: ["Collaboration"]
        """
        # get collaboration from which organization should be removed
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {
                "msg": f"Collaboration with collaboration_id={id} can not be found"
            }, HTTPStatus.NOT_FOUND

        # validate request body
        data = request.get_json(silent=True)
        try:
            data = collaboration_change_org_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # get organization which should be deleted
        data = request.get_json()
        org_id = data["id"]
        organization = db.Organization.get(org_id)
        if not organization:
            return {
                "msg": f"Organization with id={org_id} is not found"
            }, HTTPStatus.NOT_FOUND

        if not self.r.can_for_col(P.EDIT, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # delete organization and update
        collaboration.organizations.remove(organization)
        collaboration.save()
        return org_schema.dump(collaboration.organizations, many=True), HTTPStatus.OK


class CollaborationNode(ServicesResources):
    """Resource for /api/collaboration/<int:id>/node."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)

    @with_user
    def post(self, id):
        """Add node to collaboration
        ---
        description: >-
          Add node to an existing collaboration.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Add node to collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Add node to collaboration
          that your organization is a member of|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: ID of node to be added

        responses:
          201:
            description: Added node to collaboration
          404:
            description: Collaboration or node not found
          400:
            description: Node is already in collaboration
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Collaboration"]
        """
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {
                "msg": f"collaboration having collaboration_id={id} can not be found"
            }, HTTPStatus.NOT_FOUND

        if not self.r.can_for_col(P.EDIT, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # validate request body
        data = request.get_json(silent=True)
        try:
            data = collaboration_add_node_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        node = db.Node.get(data["id"])
        if not node:
            return {"msg": f"node id={data['id']} not found"}, HTTPStatus.NOT_FOUND

        if node in collaboration.nodes:
            return {
                "msg": f"node id={data['id']} is already in collaboration id={id}"
            }, HTTPStatus.BAD_REQUEST
        elif node.organization not in collaboration.organizations:
            return {
                "msg": f"Node id={data['id']} belongs to an organization that "
                f"is not part of collaboration id={id}. Please add the "
                "organization to the collaboration first"
            }, HTTPStatus.BAD_REQUEST

        collaboration.nodes.append(node)
        collaboration.save()
        return node_schema.dump(collaboration.nodes, many=True), HTTPStatus.CREATED

    @with_user
    def delete(self, id):
        """Remove node from collaboration
        ---
        description: >-
          Removes a single node from an existing collaboration.

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|Edit|❌|❌|Remove node from collaboration|\n
          |Collaboration|Collaboration|Edit|❌|❌|Remove node from
          collaboration that your organization is a member of|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Collaboration id from which the node is to be deleted.
            required: true

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  id:
                    type: integer
                    description: Node id which needs to be deleted

        responses:
          200:
            description: Ok
          404:
            description: Collaboration or node not found
          400:
            description: Node is not part of the collaboration
          401:
            description: Unauthorized

        tags: ["Collaboration"]
        """
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {
                "msg": f"collaboration having collaboration_id={id} can not be found"
            }, HTTPStatus.NOT_FOUND

        if not self.r.can_for_col(P.EDIT, collaboration.id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        node = db.Node.get(data["id"])
        if not node:
            return {"msg": f"node id={id} not found"}, HTTPStatus.NOT_FOUND

        if node not in collaboration.nodes:
            return {
                "msg": f"node id={data['id']} is not part of collaboration id={id}"
            }, HTTPStatus.BAD_REQUEST

        collaboration.nodes.remove(node)
        collaboration.save()
        return {
            "msg": f"node id={data['id']} removed from collaboration id={id}"
        }, HTTPStatus.OK
