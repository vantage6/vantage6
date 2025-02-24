import logging

from http import HTTPStatus
from flask import g, request
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.common import generate_apikey
from vantage6.common.globals import AuthStatus
from vantage6.server.resource import with_user_or_node, with_user
from vantage6.server.resource import ServicesResources
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.server.permission import (
    RuleCollection,
    Scope as S,
    Operation as P,
    PermissionManager,
)
from vantage6.server import db
from vantage6.server.resource.common.output_schema import NodeSchema
from vantage6.server.resource.common.input_schema import NodeInputSchema


module_name = __name__.split(".")[-1]
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the node resource.

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
        Nodes,
        path,
        endpoint="node_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Node,
        path + "/<int:id>",
        endpoint="node_with_id",
        methods=("GET", "DELETE", "PATCH"),
        resource_class_kwargs=services,
    )


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

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any node")
    add(
        scope=S.COLLABORATION,
        operation=P.VIEW,
        description="view any node in your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.VIEW,
        assign_to_container=True,
        description="view your own node info",
        assign_to_node=True,
    )

    add(scope=S.GLOBAL, operation=P.EDIT, description="edit any node")
    add(
        scope=S.COLLABORATION,
        operation=P.EDIT,
        description="edit any node in your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.EDIT,
        description="edit node that is part of your organization",
        assign_to_node=True,
    )

    add(
        scope=S.GLOBAL,
        operation=P.CREATE,
        description="create node for any organization",
    )
    add(
        scope=S.COLLABORATION,
        operation=P.CREATE,
        description="create node for any organization in your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.CREATE,
        description="create new node for your organization",
    )

    add(scope=S.GLOBAL, operation=P.DELETE, description="delete any node")
    add(
        scope=S.COLLABORATION,
        operation=P.DELETE,
        description="delete any node in your collaborations",
    )
    add(
        scope=S.ORGANIZATION,
        operation=P.DELETE,
        description="delete node that is part of your organization",
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
node_schema = NodeSchema()
node_input_schema = NodeInputSchema()


class NodeBase(ServicesResources):
    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r: RuleCollection = getattr(self.permissions, module_name)


class Nodes(NodeBase):
    @with_user_or_node
    def get(self):
        """Returns a list of nodes
        ---
        description: >-
            Returns a list of nodes which are part of the organization to which
            the user or node belongs. In case an administrator account makes
            this request, all nodes from all organizations are returned.\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Node|Global|View|❌|❌|View any node information|\n
            |Node|Collaboration|View|❌|❌|View any node information for nodes
            in your collaborations|\n
            |Node|Organization|View|✅|✅|View node information for nodes that
            belong to your organization|\n

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
            name: organization_id
            schema:
              type: integer
            description: Organization id
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Collaboration id
          - in: query
            name: study_id
            schema:
              type: integer
            description: Study id
          - in: query
            name: status
            schema:
              type: string
            description: Node status ('online', 'offline')
          - in: query
            name: ip
            schema:
              type: string
            description: Node IP address
          - in: query
            name: last_seen_from
            schema:
              type: date (yyyy-mm-dd)
            description: Show only nodes seen since this date
          - in: query
            name: last_seen_till
            schema:
              type: date (yyyy-mm-dd)
            description: Show only nodes last seen before this date
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
                description: Improper values for pagination or sorting
                  parameters

        security:
            - bearerAuth: []

        tags: ["Node"]
        """
        q = select(db.Node)
        auth_org_id = self.obtain_organization_id()
        args = request.args

        if "organization_id" in args:
            if not self.r.can_for_org(P.VIEW, int(args["organization_id"])):
                return {
                    "msg": "You lack the permission view nodes from the "
                    f'organization with id {args["organization_id"]}!'
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Node.organization_id == args["organization_id"])

        if "collaboration_id" in args:
            collaboration_id = int(args["collaboration_id"])
            if not self.r.can_for_col(P.VIEW, collaboration_id):
                return {
                    "msg": "You lack the permission view nodes from the "
                    f"collaboration with id {collaboration_id}!"
                }, HTTPStatus.UNAUTHORIZED
            q = q.filter(db.Node.collaboration_id == collaboration_id)

        if "study_id" in args:
            study_id = int(args["study_id"])
            study = db.Study.get(study_id)
            if not self.r.can_for_col(P.VIEW, study.collaboration_id):
                return {
                    "msg": "You lack the permission view nodes from collaboration "
                    f"{study.collaboration_id} contains the study with id {study_id}!"
                }, HTTPStatus.UNAUTHORIZED
            q = (
                q.join(db.Organization)
                .join(db.StudyMember)
                .join(db.Study)
                .filter(
                    db.Study.id == study_id,
                    db.Node.collaboration_id == study.collaboration_id,
                )
            )

        for param in ["status", "ip"]:
            if param in args:
                q = q.filter(getattr(db.Node, param) == args[param])
        if "name" in args:
            q = q.filter(db.Node.name.like(args["name"]))

        if "last_seen_till" in args:
            q = q.filter(db.Node.last_seen <= args["last_seen_till"])
        if "last_seen_from" in args:
            q = q.filter(db.Node.last_seen >= args["last_seen_from"])

        if not self.r.v_glo.can():
            if self.r.v_col.can():
                q = q.filter(
                    db.Node.collaboration_id.in_(
                        [col.id for col in self.obtain_auth_collaborations()]
                    )
                )
            elif self.r.v_org.can():
                # only the results of the user's organization are returned
                q = q.filter(db.Node.organization_id == auth_org_id)
            else:
                return {
                    "msg": "You lack the permission to do that!"
                }, HTTPStatus.UNAUTHORIZED

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.Node)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.INTERNAL_SERVER_ERROR

        # model serialization
        return self.response(page, node_schema)

    # TODO the example in swagger docs for this doesn't include
    # organization_id. Find out why
    @with_user
    def post(self):
        """Create node
        ---
        description: >-
          Creates a new node-account belonging to a specific organization and
          collaboration which is specified in the POST body.\n
          The organization of the user needs to be within the collaboration.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Node|Global|Create|❌|❌|Create a new node account belonging to a
          specific organization in any collaboration|\n
          |Node|Collaboration|Create|❌|❌|Create a new node account belonging
          to a specific organization in your collaborations|\n
          |Node|Organization|Create|❌|❌|Create a new node account belonging
          to your organization|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  collaboration_id:
                    type: integer
                    description: Collaboration id
                  organization_id:
                    type: integer
                    description: Organization id. If not provided, this
                      defaults to the organization of the user creating the
                      node.
                  name:
                    type: string
                    description: Human-readable name. If not provided a name
                      is generated based on organization and collaboration
                      name.

        responses:
          201:
            description: New node-account created
          404:
            description: Collaboration specified by id does not exists
          400:
            description: Organization is not part of the collaboration, or it
              already has a node for this collaboration, or the node name is
              not unique.
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        data = request.get_json(silent=True)
        # validate request body
        try:
            data = node_input_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check that the collaboration exists
        collaboration = db.Collaboration.get(data["collaboration_id"])
        if not collaboration:
            return {
                "msg": f"collaboration id={data['collaboration_id']} " "does not exist"
            }, HTTPStatus.NOT_FOUND  # 404

        org_id = (
            data["organization_id"]
            if data.get("organization_id") is not None
            else g.user.organization_id
        )
        organization = db.Organization.get(org_id)

        # check that the organization exists
        if not organization:
            return {
                "msg": f"organization id={org_id} does not exist"
            }, HTTPStatus.NOT_FOUND

        # check permissions
        if not self.r.can_for_org(P.CREATE, org_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # we need to check that the organization belongs to the
        # collaboration
        if not (organization in collaboration.organizations):
            return {
                "msg": f"The organization id={org_id} is not part of "
                f"collabotation id={collaboration.id}. Add it first!"
            }, HTTPStatus.BAD_REQUEST

        # verify that this node does not already exist
        if db.Node.exists_by_id(organization.id, collaboration.id):
            return {
                "msg": f"Organization id={organization.id} already has a "
                f"node for collaboration id={collaboration.id}"
            }, HTTPStatus.BAD_REQUEST

        # if no name is provided, generate one
        name = (
            data["name"]
            if "name" in data
            else f"{organization.name} - {collaboration.name} Node"
        )
        if db.Node.exists("name", name):
            return {
                "msg": f"Node with name '{name}' already exists!"
            }, HTTPStatus.BAD_REQUEST

        # Ok we're good to go!
        api_key = generate_apikey()
        node = db.Node(
            name=name,
            collaboration=collaboration,
            organization=organization,
            api_key=api_key,
            status=AuthStatus.OFFLINE.value,
        )
        node.save()

        # Return the node information to the user. Manually return the api_key
        # to the user as the hashed key is not returned
        node_json = node_schema.dump(node)
        node_json["api_key"] = api_key
        return node_json, HTTPStatus.CREATED  # 201


class Node(NodeBase):
    @with_user_or_node
    def get(self, id):
        """Get node
        ---
        description: >-
          Returns the node by the specified id.\n
          Only returns the node if the user or node has the required
          permission.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Node|Global|View|❌|❌|View any node information|\n
          |Node|Collaboration|View|❌|❌|View any node information for nodes
          within your collaborations|\n
          |Node|Organization|View|✅|✅|View node information for nodes that
          belong to your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id_
            schema:
              type: integer
              minimum: 1
            description: Node id
            required: tr

        responses:
          200:
            description: Ok
          404:
            description: Node with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        node = db.Node.get(id)
        if not node:
            return {"msg": f"Node id={id} is not found!"}, HTTPStatus.NOT_FOUND

        # check permissions
        if not self.r.can_for_org(P.VIEW, node.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        return node_schema.dump(node, many=False), HTTPStatus.OK

    @with_user
    def delete(self, id):
        """
        Delete node
        ---
        description: >-
          Delete node from organization. Only users that belong to the
          organization of the node can delete it.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Node|Global|Delete|❌|❌|Delete a node|\n
          |Node|Collaboration|Delete|❌|❌|Delete a node that belongs to
          one of the organizations in your collaborations|\n
          |Node|Organization|Delete|❌|❌|Delete a node that belongs to your
          organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id_
            schema:
              type: integer
              minimum: 1
            description: Node id
            required: tr

        responses:
          200:
            description: Ok, node is deleted
          404:
            description: Node with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        node = db.Node.get(id)
        if not node:
            return {"msg": f"Node id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.r.can_for_org(P.DELETE, node.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        node.delete()
        return {"msg": f"Successfully deleted node id={id}"}, HTTPStatus.OK

    @with_user_or_node
    def patch(self, id):
        """Update node
        ---
        description: >-
          Update the node specified by the id. Only a user or node that belongs
          to the organization of the node are allowed to update it.\n
          If the node does not exists it is created as a new node.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Node|Global|Edit|❌|❌|Update a node specified by id|\n
          |Node|Collaboration|Edit|❌|❌|Update a node specified by id which
          is part of one of your collaborations|\n
          |Node|Organization|Edit|❌|❌|Update a node specified by id which is
          part of your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id_
            schema:
              type: integer
            description: Node id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  name:
                    type: string
                    description: Node name
                  ip:
                    type: string
                    description: The node's VPN IP address
                  clear_ip:
                    type: boolean
                    description: Clear the node's VPN IP address

        responses:
          200:
            description: Ok, node is updated
          400:
            description: A node already exist for this organization in this
              collaboration, or a node already exists with this name
          401:
            description: Unauthorized
          404:
            description: Organization or collaboration not found

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        data = request.get_json(silent=True)
        # validate request body
        try:
            data = node_input_schema.load(data, partial=True)
        except ValidationError as e:
            return {
                "msg": "Request body is incorrect",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # for patching, organization_id and collaboration_id are not allowed fields
        if "organization_id" in data:
            return {"msg": "Organization id cannot be updated!"}, HTTPStatus.BAD_REQUEST
        elif "collaboration_id" in data:
            return {
                "msg": "Collaboration id cannot be updated!"
            }, HTTPStatus.BAD_REQUEST

        node = db.Node.get(id)
        if not node:
            return {"msg": f"Node id={id} not found!"}, HTTPStatus.NOT_FOUND

        if not self.r.can_for_org(P.EDIT, node.organization_id):
            return {
                "msg": "You lack the permission to do that!"
            }, HTTPStatus.UNAUTHORIZED

        # update fields
        if "name" in data:
            name = data["name"]
            if node.name != name and db.Node.exists("name", name):
                return {
                    "msg": f"Node name '{name}' already exists!"
                }, HTTPStatus.BAD_REQUEST
            node.name = name

        # update node IP address if it is given
        ip = data.get("ip")
        if ip:
            node.ip = ip
        elif data.get("clear_ip"):
            node.ip = None

        node.save()
        return node_schema.dump(node), HTTPStatus.OK
