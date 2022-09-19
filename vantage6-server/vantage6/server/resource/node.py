# -*- coding: utf-8 -*-
import logging
import uuid

from http import HTTPStatus
from flask import g, request
from flask_restful import reqparse


from vantage6.server.resource import with_user_or_node, with_user
from vantage6.server.resource import ServicesResources
from vantage6.server.resource.pagination import Pagination
from vantage6.server.permission import (Scope as S,
                                        Operation as P, PermissionManager)
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server import db
from vantage6.server.resource._schema import NodeSchema


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Nodes,
        path,
        endpoint='node_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Node,
        path + '/<int:id>',
        endpoint='node_with_id',
        methods=('GET', 'DELETE', 'PATCH'),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permission: PermissionManager):
    add = permission.appender("node")

    add(scope=S.GLOBAL, operation=P.VIEW, description="view any node")
    add(scope=S.ORGANIZATION, operation=P.VIEW, assign_to_container=True,
        description="view your own node info", assign_to_node=True)

    add(scope=S.GLOBAL, operation=P.EDIT, description="edit any node")
    add(scope=S.ORGANIZATION, operation=P.EDIT,
        description="edit node that is part of your organization",
        assign_to_node=True)

    add(scope=S.GLOBAL, operation=P.CREATE,
        description="create node for any organization")
    add(scope=S.ORGANIZATION, operation=P.CREATE,
        description="create new node for your organization")

    add(scope=S.GLOBAL, operation=P.DELETE, description="delete any node")
    add(scope=S.ORGANIZATION, operation=P.DELETE,
        description="delete node that is part of your organization")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
node_schema = NodeSchema()


class NodeBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


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
            name: include
            schema:
              type: string
            description: Include 'metadata' to get pagination metadata. Note
              that this will put the actual data in an envelope.
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page

        responses:
            200:
                description: Ok
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Node"]
        """
        q = DatabaseSessionManager.get_session().query(db.Node)
        auth_org_id = self.obtain_organization_id()
        args = request.args

        for param in ['organization_id', 'collaboration_id', 'status', 'ip']:
            if param in args:
                q = q.filter(getattr(db.Node, param) == args[param])
        if 'name' in args:
            q = q.filter(db.Node.name.like(args['name']))

        if 'last_seen_till' in args:
            q = q.filter(db.Node.last_seen <= args['last_seen_till'])
        if 'last_seen_from' in args:
            q = q.filter(db.Node.last_seen >= args['last_seen_from'])

        if not self.r.v_glo.can():
            if self.r.v_org.can():
                # only the results of the user's organization are returned
                q = q.filter(db.Node.organization_id == auth_org_id)
            else:
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate results
        page = Pagination.from_query(q, request)

        # model serialization
        return self.response(page, node_schema)

    # TODO the example in swagger docs for this doesn't include
    # organization_id. Find out why
    @with_user
    def post(self):
        """Create node
        ---
        description: >-
          Creates a new node-account belonging to a specific collaboration
          which is specified in the POST body.\n
          The organization of the user needs to be within the collaboration.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Node|Global|Create|❌|❌|Create a new node account belonging to a
          specific collaboration|\n
          |Node|Organization|Create|❌|❌|Create a new node account belonging
          to a specific organization which is also part of the collaboration|\n

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
                    description: Organization id
                  name:
                    type: str
                    description: Human-readable name, if not profided a name
                      is generated

        responses:
          201:
            description: New node-account created
          404:
            description: Collaboration specified by id does not exists
          400:
            description: Organization is not part of the collaboration or it
              already has a node for this collaboration
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        parser = reqparse.RequestParser()
        parser.add_argument("collaboration_id", type=int, required=True,
                            help="This field cannot be left blank!")
        parser.add_argument("organization_id", type=int, required=False)
        parser.add_argument("name", type=str, required=False)
        data = parser.parse_args()

        collaboration = db.Collaboration.get(data["collaboration_id"])

        # check that the collaboration exists
        if not collaboration:
            return {"msg": f"collaboration id={data['collaboration_id']} "
                    "does not exist"}, HTTPStatus.NOT_FOUND  # 404

        # check permissions
        org_id = data["organization_id"]
        user_org_id = g.user.organization.id
        if not self.r.c_glo.can():
            own = not org_id or org_id == user_org_id
            if not (self.r.c_org.can() and own):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            else:
                org_id = g.user.organization.id
        organization = db.Organization.get(org_id or user_org_id)

        # we need to check that the organization belongs to the
        # collaboration
        if not (organization in collaboration.organizations):
            return {'msg': f'The organization id={org_id} is not part of '
                    f'collabotation id={collaboration.id}. Add it first!'}, \
                        HTTPStatus.BAD_REQUEST

        # verify that this node does not already exist
        if db.Node.exists(organization.id, collaboration.id):
            return {'msg': f'Organization id={organization.id} already has a '
                    f'node for collaboration id={collaboration.id}'}, \
                        HTTPStatus.BAD_REQUEST

        # if no name is profided, generate one
        name = data['name'] if data['name'] else \
            f"{organization.name} - {collaboration.name} Node"

        # Ok we're good to go!
        api_key = str(uuid.uuid4())
        node = db.Node(
            name=name,
            collaboration=collaboration,
            organization=organization,
            api_key=api_key
        )
        node.save()

        # Return the node information to the user. Manually return the api_key
        # to the user as the hashed key is not returned
        node_json = node_schema.dump(node).data
        node_json['api_key'] = api_key
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
          |Node|Organization|View|✅|✅|View node information for nodes that
          belong to your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
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
            return {'msg': f'Node id={id} is not found!'}, HTTPStatus.NOT_FOUND

        # obtain authenticated model
        auth = self.obtain_auth()

        # check permissions
        if not self.r.v_glo.can():
            same_org = auth.organization.id == node.organization.id
            if not (self.r.v_org.can() and same_org):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return node_schema.dump(node, many=False).data, HTTPStatus.OK

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
          |Node|Organization|Delete|❌|❌|Delete a node that belongs to your
          organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
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

        if not self.r.d_glo.can():
            own = node.organization == g.user.organization
            if not (self.r.d_org.can() and own):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

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
          |Node|Organization|Edit|❌|❌|Update a node specified by id which is
          part of your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Node id
            required: tr

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
                    description: Organization id
                  name:
                    type: string
                    description: Node name
                  ip:
                    type: string
                    description: The node's VPN IP address

        responses:
          200:
            description: Ok, node is updated
          400:
            description: A node already exist for this organization in this
              collaboration
          401:
            description: Unauthorized
          404:
            description: Organization or collaboration not found

        security:
          - bearerAuth: []

        tags: ["Node"]
        """
        node = db.Node.get(id)
        if not node:
            return {'msg': f'Node id={id} not found!'}, HTTPStatus.NOT_FOUND

        auth = g.user or g.node

        if not self.r.e_glo.can():
            own = auth.organization.id == node.organization.id
            if not (self.r.e_org.can() and own):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        data = request.get_json()

        # update fields
        if 'name' in data:
            node.name = data['name']

        # organization goes before collaboration (!)
        org_id = data.get('organization_id')
        updated_org = org_id and org_id != node.organization.id
        if updated_org:
            if not self.r.e_glo.can():
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED
            organization = db.Organization.get(data['organization_id'])
            if not organization:
                return {'msg': f'Organization id={data["organization_id"]} '
                        'not found!'}, HTTPStatus.NOT_FOUND
            node.organization = organization

        col_id = data.get('collaboration_id')
        updated_col = col_id and col_id != node.collaboration.id
        if updated_col:
            collaboration = db.Collaboration.get(data['collaboration_id'])
            if not collaboration:
                return {'msg': f'collaboration id={data["collaboration_id"]}'
                        'not found!'}, HTTPStatus.NOT_FOUND

            if not self.r.e_glo.can():
                if auth.organization not in collaboration.organizations:
                    return {'msg': f'Organization id={auth.organization.id} '
                            'of this node is not part of this collaboration id'
                            f'={collaboration.id}'}

            node.collaboration = collaboration

        # validate that node does not already exist when we change either
        # the organization and/or collaboration
        if updated_org or updated_col:
            if db.Node.exists(node.organization.id, node.collaboration.id):
                return {'msg': 'A node with organization id='
                        f'{node.organization.id} and collaboration id='
                        f'{node.collaboration.id} already exists!'}, \
                            HTTPStatus.BAD_REQUEST

        # update node IP address if it is given
        ip = data.get('ip')
        if ip:
            node.ip = ip

        node.save()
        return node_schema.dump(node).data, HTTPStatus.OK
