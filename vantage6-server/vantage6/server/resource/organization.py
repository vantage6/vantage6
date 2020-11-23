# -*- coding: utf-8 -*-
import logging

from flask import request
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6.server import db
from vantage6.server.resource import (
    with_user_or_node, only_for,
    ServicesResources
)
from vantage6.server.resource._schema import (
    OrganizationSchema,
    CollaborationSchema,
    NodeSchema
)


module_name = __name__.split('.')[-1]
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
        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"organization id={id} not found"}, \
                HTTPStatus.NOT_FOUND

        return self.org_schema.dump(organization, many=not id).data, \
            HTTPStatus.OK

    @only_for(["user"])
    @swag_from(str(Path(r"swagger/post_organization_without_id.yaml")),
               endpoint='organization_without_id')
    def post(self):
        """Create a new organization."""

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

        return self.org_schema.dump(
            organization, many=False
        ).data, HTTPStatus.CREATED

    @only_for(["user", "node"])
    def patch(self, id):
        """Update organization."""

        organization = db.Organization.get(id)
        if not organization:
            return {"msg": f"Organization with id {id} not found"}, \
                HTTPStatus.NOT_FOUND

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
