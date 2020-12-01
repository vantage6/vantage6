# -*- coding: utf-8 -*-
import logging

from flask import request, g
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.permission import (
    register_rule,
    Scope as S,
    Operation as P
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
view_any = register_rule("manage_organization", scope=S.GLOBAL,
                         operation=P.VIEW,
                         description="view any organization")
view_org = register_rule("manage_organization", scope=S.ORGANIZATION,
                         operation=P.VIEW,
                         description="view your own organization info",
                         assign_to_container=True, assign_to_node=True)
view_col = register_rule('manage_organization', S.COLLABORATION,
                         P.VIEW,
                         description='view collaborating organizations',
                         assign_to_container=True, assign_to_node=True)
edit_any = register_rule("manage_organization", scope=S.GLOBAL,
                         operation=P.EDIT,
                         description="edit any organization")
edit_org = register_rule("manage_organization", scope=S.ORGANIZATION,
                         operation=P.EDIT,
                         description="edit your own organization info")
crte_any = register_rule("manage_organization", scope=S.GLOBAL,
                         operation=P.CREATE,
                         description="create a new organization")
delt_any = register_rule("manage_organization", scope=S.GLOBAL,
                         operation=P.DELETE,
                         description="delete any organization")
delt_org = register_rule("manage_organization", scope=S.ORGANIZATION,
                         operation=P.DELETE,
                         description="delete your organization")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Organization(ServicesResources):

    org_schema = OrganizationSchema()

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
        accepted = False

        # check if he want a single or all organizations
        if id:
            # Check if auth has enough permissions
            if view_any.can():
                accepted = True
            elif view_col.can():
                # check if the organization is whithin a collaboration
                for col in auth_org.collaborations:
                    if req_org in col.organizations:
                        accepted = True
                if req_org == auth_org:
                    accepted = True
            elif view_org.can():
                accepted = auth_org == req_org

            if accepted:
                return self.org_schema.dump(req_org, many=False).data, \
                    HTTPStatus.OK

        # filter de list of organizations based on the scope
        else:
            organizations = []
            if view_any.can():
                organizations = req_org
                accepted = True
            elif view_col.can():
                for col in auth_org.collaborations:
                    for org in col.organizations:
                        if org not in organizations:
                            organizations.append(org)
                organizations.append(auth_org)
                accepted = True
            elif view_org.can():
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

        if not crte_any.can():
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

    @only_for(["user"])
    def patch(self, id):
        """Update organization."""

        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"Organization with id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        if not edit_any.can():
            if not (edit_org.can() and id == g.user.organization.id):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        fields = ["name", "address1", "address2", "zipcode", "country",
                  "public_key", "domain"]
        for field in fields:
            if data.get(field):
                setattr(organization, field, data.get(field))

        organization.save()
        return organization, HTTPStatus.OK


class OrganizationCollaboration(ServicesResources):
    """Collaborations for a specific organization."""

    col_schema = CollaborationSchema()

    @only_for(["user", "node"])
    @swag_from(str(Path(r"swagger/get_organization_collaboration.yaml")),
               endpoint='organization_collaboration')
    def get(self, id):
        organization = db.Organization.get(id)
        if not organization:
            return {"msg": "organization id={} not found".format(id)}, \
                HTTPStatus.NOT_FOUND

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
            return {"msg": "organization id={} not found".format(id)}, \
                HTTPStatus.NOT_FOUND

        return self.nod_schema.dump(organization.nodes, many=True).data, \
            HTTPStatus.OK
