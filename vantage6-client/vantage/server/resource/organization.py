# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/organization'
"""
from __future__ import print_function, unicode_literals

import logging
import base64

from flask import request
from flask_restful import Resource
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage.server.resource import with_user_or_node, with_user, only_for
from ._schema import *


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, API_BASE):

    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Organization,
        path,
        endpoint='organization_without_id',
        methods=('GET', 'POST')
     )
    api.add_resource(
        Organization,
        path + '/<int:id>',
        endpoint='organization_with_id',
        methods=('GET', 'PATCH')
    )
    api.add_resource(
        OrganizationCollaboration,
        path + '/<int:id>/collaboration',
        endpoint='organization_collaboration',
        methods=('GET',)
    )
    api.add_resource(
        OrganizationNode,
        path + '/<int:id>/node',
        endpoint='organization_node',
        methods=('GET',)
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Organization(Resource):

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
            public_key=data.get('public_key', '')
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
        fields = ["name", "address1", "address2", "zipcode", "country", \
            "public_key"]
        for field in fields:
            if data.get(field):
                setattr(organization, field, data.get(field))
        
        organization.save()
        return organization, HTTPStatus.OK

class OrganizationCollaboration(Resource):
    """Collaborations for a specific organization."""

    col_schema = CollaborationSchema()

    @only_for(["user", "node"])
    @swag_from(str(Path(r"swagger/get_organization_collaboration.yaml")), endpoint='organization_collaboration')
    def get(self, id):
        organization = db.Organization.get(id)
        if not organization:
            return {"msg": "organization id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        return self.col_schema.dump(organization.collaborations, many=True).data, HTTPStatus.OK

    # @with_user
    # def post(self, id):
    #     organization = db.Organization.get(id)
    #     if not organization:
    #         return {"msg": "organization id={} not found".format(id)}, HTTPStatus.NOT_FOUND
    #
    #     data = request.get_json()
    #     collaboration = db.Collaboration.get(data['id'])
    #     if not collaboration:
    #         return {"msg": "collaboration id={} is not found".format(data['id'])}, HTTPStatus.NOT_FOUND
    #
    #     organization.collaborations.append(collaboration)
    #     organization.save()
    #     return self.col_schema.dump(organization.collaborations, many=True).data, HTTPStatus.OK


class OrganizationNode(Resource):
    """Resource for /api/organization/<int:id>/node."""

    nod_schema = NodeSchema()

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_organization_node.yaml")), endpoint='organization_node')
    def get(self, id):
        """Return a list of Nodes."""
        organization = db.Organization.get(id)
        if not organization:
            return {"msg": "organization id={} not found".format(id)}, HTTPStatus.NOT_FOUND

        return self.nod_schema.dump(organization.nodes, many=True).data, HTTPStatus.OK

    # @with_user
    # def post(self, id):
    #     """Create new node"""
    #     organization = db.Organization.get(id)
    #     if not organization:
    #         return {"msg": "organization id={} not found".format(id)}, HTTPStatus.NOT_FOUND
    #
    #     data = request.get_json()
    #
    #     db.Node(
    #         name="{} - {} Node".format(organization.name, collaboration.name),
    #         collaboration=collaboration,
    #         organization=organization,
    #         api_key=api_key
    #     )
    #     node.save()
    #
    #     return node


