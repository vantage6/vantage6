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
from vantage6.server.permission import (Scope as S,
                                        Operation as P, PermissionManager)
from vantage6.server import db
from vantage6.server.resource._schema import NodeSchema


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Node,
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
        description="edit node that is part of your organization")

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
class Node(ServicesResources):

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    # Schemas
    node_schema = NodeSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_node_with_id.yaml")),
               endpoint='node_with_id')
    @swag_from(str(Path(r"swagger/get_node_without_id.yaml")),
               endpoint='node_without_id')
    def get(self, id=None):
        """ View node that belong in the same organization"""
        node = db.Node.get(id)
        if not node:
            return {'msg': f'Node id={id} is not found!'}, HTTPStatus.NOT_FOUND

        auth = g.user or g.node
        if id:
            if not self.r.v_glo.can():
                same_org = auth.organization.id == node.organization.id
                if not (self.r.v_org.can() and same_org):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED
        else:
            if not self.r.v_glo.can():
                if self.r.v_org.can():
                    # only the results of the user's organization are returned
                    org_id = auth.organization_id
                    node = [n for n in node if n.organization_id == org_id]
                else:
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

        return self.node_schema.dump(node, many=not id).data, HTTPStatus.OK

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
        node = db.Node(
            name=f"{organization.name} - {collaboration.name} Node",
            collaboration=collaboration,
            organization=organization,
            api_key=str(uuid.uuid1())
        )
        node.save()

        return self.node_schema.dump(node).data, HTTPStatus.CREATED  # 201

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

    @with_user
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

            # check that the users organization is part of the collaboration
            # we are going to assign the node to.
            if not self.r.e_glo.can():
                if auth.organization not in collaboration.organizations:
                    return {'msg': f'Organization id={auth.organization.id} of'
                            ' this node is not part of this collaboration id='
                            f'{collaboration.id}'}

            node.collaboration = collaboration

        # validate that node does not already exist when we change either
        # the organization and/or collaboration
        if updated_org or updated_col:
            if db.Node.exists(node.organization.id, node.collaboration.id):
                return {'msg': 'A node with organization id='
                        f'{node.organization.id} and collaboration id='
                        f'{node.collaboration.id} already exists!'}, \
                            HTTPStatus.BAD_REQUEST

        node.save()
        return self.node_schema.dump(node).data, HTTPStatus.OK
