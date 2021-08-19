# -*- coding: utf-8 -*-
import logging

from flask import request, g
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager
)
from vantage6.server.resource import (
    with_user_or_node, only_for,
    ServicesResources
)
from vantage6.server.resource._schema import (
    OrganizationSchema,
    CollaborationSchema,
    NodeSchema
)


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Organization,
        path,
        endpoint='organization_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
     )
    api.add_resource(
        Organization,
        path + '/<int:id>',
        endpoint='organization_with_id',
        methods=('GET', 'PATCH'),
        resource_class_kwargs=services
    )
    api.add_resource(
        OrganizationCollaboration,
        path + '/<int:id>/collaboration',
        endpoint='organization_collaboration',
        methods=('GET',),
        resource_class_kwargs=services
    )
    api.add_resource(
        OrganizationNode,
        path + '/<int:id>/node',
        endpoint='organization_node',
        methods=('GET',),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):
    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW,
        description="view any organization")
    add(scope=S.ORGANIZATION, operation=P.VIEW,
        description="view your own organization info",
        assign_to_container=True, assign_to_node=True)
    add(scope=S.COLLABORATION, operation=P.VIEW,
        description='view collaborating organizations',
        assign_to_container=True, assign_to_node=True)
    add(scope=S.GLOBAL, operation=P.EDIT,
        description="edit any organization")
    add(scope=S.ORGANIZATION, operation=P.EDIT,
        description="edit your own organization info", assign_to_node=True)
    add(scope=S.GLOBAL, operation=P.CREATE,
        description="create a new organization")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Organization(ServicesResources):

    org_schema = OrganizationSchema()

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(["user", "node", "container"])
    @swag_from(str(Path(r"swagger/get_organization_with_id.yaml")),
               endpoint='organization_with_id')
    @swag_from(str(Path(r"swagger/get_organization_without_id.yaml")),
               endpoint='organization_without_id')
    def get(self, id=None):

        # determine the organization to which the auth belongs
        if g.container:
            auth_org_id = g.container["organization_id"]
        elif g.node:
            auth_org_id = g.node.organization_id
        else:  # g.user:
            auth_org_id = g.user.organization_id
        auth_org = db.Organization.get(auth_org_id)

        # retrieve requested organization
        req_org = db.Organization.get(id)
        if not req_org:
            return {'msg': f'Organization id={id} not found!'}, \
                HTTPStatus.NOT_FOUND

        accepted = False
        # check if he want a single or all organizations
        if id:
            # Check if auth has enough permissions
            if self.r.v_glo.can():
                accepted = True
            elif self.r.v_col.can():
                # check if the organization is whithin a collaboration
                for col in auth_org.collaborations:
                    if req_org in col.organizations:
                        accepted = True
                if req_org == auth_org:
                    accepted = True
            elif self.r.v_org.can():
                accepted = auth_org == req_org

            if accepted:
                return self.org_schema.dump(req_org, many=False).data, \
                    HTTPStatus.OK

        # filter de list of organizations based on the scope
        else:
            organizations = []
            if self.r.v_glo.can():
                organizations = req_org
                accepted = True
            elif self.r.v_col.can():
                for col in auth_org.collaborations:
                    for org in col.organizations:
                        if org not in organizations:
                            organizations.append(org)
                organizations.append(auth_org)
                accepted = True
            elif self.r.v_org.can():
                organizations = [auth_org]
                accepted = True

            if accepted:
                return self.org_schema.dump(organizations, many=True).data, \
                    HTTPStatus.OK

        # If you get here you do not have permission to see anything
        return {'msg': 'You do not have permission to do that!'}, \
            HTTPStatus.UNAUTHORIZED

    @only_for(["user"])
    @swag_from(str(Path(r"swagger/post_organization_without_id.yaml")),
               endpoint='organization_without_id')
    def post(self):
        """Create a new organization."""

        if not self.r.c_glo.can():
            return {'msg': 'You lack the permissions to do that!'},\
                HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        organization = db.Organization(
            name=data.get('name', ''),
            address1=data.get('address1', ''),
            address2=data.get('address2' ''),
            zipcode=data.get('zipcode', ''),
            country=data.get('country', ''),
            public_key=data.get('public_key', ''),
            domain=data.get('domain', '')
        )
        organization.save()

        return self.org_schema.dump(organization, many=False).data, \
            HTTPStatus.CREATED

    @only_for(["user", "node"])
    @swag_from(str(Path(r"swagger/patch_organization_with_id.yaml")),
               endpoint='organization_with_id')
    def patch(self, id):
        """Update organization."""

        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"Organization with id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if not (
            self.r.e_glo.can() or
            (self.r.e_org.can() and g.user and id == g.user.organization.id) or
            (self.r.e_org.can() and g.node and id == g.node.organization.id)
        ):
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        fields = ["name", "address1", "address2", "zipcode", "country",
                  "public_key", "domain"]
        for field in fields:
            if field in data:
                setattr(organization, field, data[field])

        organization.save()
        return self.org_schema.dump(organization, many=False).data, \
            HTTPStatus.OK


class OrganizationCollaboration(ServicesResources):
    """Collaborations for a specific organization."""

    col_schema = CollaborationSchema()

    @only_for(["user", "node"])
    @swag_from(str(Path(r"swagger/get_organization_collaboration.yaml")),
               endpoint='organization_collaboration')
    def get(self, id):

        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"organization id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if g.node:
            auth_org_id = g.node.organization.id
        else:  # g.user:
            auth_org_id = g.user.organization.id

        if not self.permissions.collaboration.v_glo.can():
            if not (self.permissions.collaboration.v_org.can() and
                    auth_org_id == id):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return self.col_schema.dump(
            organization.collaborations,
            many=True
        ).data, HTTPStatus.OK


class OrganizationNode(ServicesResources):
    """Resource for /api/organization/<int:id>/node."""

    nod_schema = NodeSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_organization_node.yaml")),
               endpoint='organization_node')
    def get(self, id):
        """Return a list of Nodes."""
        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"organization id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if g.user:
            auth_org_id = g.user.organization.id
        else:  # g.node
            auth_org_id = g.node.organization.id

        if not self.permissions.node.v_glo.can():
            if not (self.permissions.node.v_org.can() and id == auth_org_id):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return self.nod_schema.dump(organization.nodes, many=True).data, \
            HTTPStatus.OK
