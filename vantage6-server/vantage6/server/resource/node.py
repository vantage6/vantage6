# -*- coding: utf-8 -*-
import logging
import uuid

from pathlib import Path
from http import HTTPStatus
from flasgger.utils import swag_from
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
            this request, all nodes from all organizations are returned.\n\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Node|Global|View|❌|❌|View any node information|\n
            |Node|Organization|View|✅|✅|View node information for nodes that
            belong to your organization|\n\n

            Accessible as: `user` and `node`.\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.\n\n

        parameters:
            - in: query
              name: include
              schema:
                type: string
              description: what to include in the output ('metadata')
            - in: query
              name: page
              schema:
                type: integer
              description: page number for pagination
            - in: query
              name: per_page
              schema:
                type: integer
              description: number of items per page

        responses:
            200:
                description: Ok
            401:
                description: Unauthorized or missing permissions

        security:
            - bearerAuth: []

        tags: ["Node"]
        """
        q = DatabaseSessionManager.get_session().query(db.Node)
        auth_org_id = self.obtain_organization_id()
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

    @with_user
    @swag_from(str(Path(r"swagger/post_node_without_node_id.yaml")),
               endpoint='node_without_id')
    def post(self):
        """ Create a new node account"""
        parser = reqparse.RequestParser()
        parser.add_argument("collaboration_id", type=int, required=True,
                            help="This field cannot be left blank!")
        parser.add_argument("organization_id", type=int, required=False)
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

        # Ok we're good to go!
        api_key = str(uuid.uuid1())
        node = db.Node(
            name=f"{organization.name} - {collaboration.name} Node",
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
    @swag_from(str(Path(r"swagger/get_node_with_id.yaml")),
               endpoint='node_with_id')
    def get(self, id):
        """ View node that belong in the same organization"""
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
    @swag_from(str(Path(r"swagger/delete_node_with_id.yaml")),
               endpoint='node_with_id')
    def delete(self, id):
        """delete node account"""
        node = db.Node.get(id)
        if not node:
            return {"msg": f"Node id={id} not found"}, HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            own = node.organization == g.user.organization
            if not (self.r.d_org.can() and own):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        node.delete()
        return {"msg": f"successfully deleted node id={id}"}, HTTPStatus.OK

    @with_user_or_node
    @swag_from(str(Path(r"swagger/patch_node_with_id.yaml")),
               endpoint='node_with_id')
    def patch(self, id):
        """update existing node"""
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

        if 'ip' in data:
            node.ip = data['ip']

        # validate that node does not already exist when we change either
        # the organization and/or collaboration
        if updated_org or updated_col:
            if db.Node.exists(node.organization.id, node.collaboration.id):
                return {'msg': 'A node with organization id='
                        f'{node.organization.id} and collaboration id='
                        f'{node.collaboration.id} already exists!'}, \
                            HTTPStatus.BAD_REQUEST

        node.save()
        return node_schema.dump(node).data, HTTPStatus.OK
