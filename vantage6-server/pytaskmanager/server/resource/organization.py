# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/organization'
"""
from __future__ import print_function, unicode_literals
import os, os.path

from flask import request
from flask_restful import Resource
from flask_jwt_extended import jwt_required, jwt_refresh_token_required, create_access_token, create_refresh_token, get_jwt_identity

import logging
module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)

from .. import db

from . import with_user_or_node, with_node
from ._schema import *


def setup(api, API_BASE):
    module_name = __name__.split('.')[-1]
    path = "/".join([API_BASE, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))
    
    api.add_resource(Organization,
        path,
        path + '/<int:id>',
        endpoint='organization'
    )
    api.add_resource(OrganizationCollaboration,
        path + '/<int:id>',
        path + '/<int:id>/<int:collaboration_id>',
    )
    api.add_resource(OrganizationNode,
        path + '/<int:id>/node',
        path + '/<int:id>/node/<int:node_id>',
    )

# Schemas
org_schema = OrganizationSchema()


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Organization(Resource):
    
    @jwt_required
    def get(self, id=None):
        orgs = db.Organization.get(id)
        return org_schema.dump(orgs, many=not id)

    @jwt_required
    def post(self):
        """Create a new organization."""
        data = request.get_json()
        org = db.Organization()

        for p in ['name', 'address1', 'address2', 'zipcode', 'country']:
            setattr(org, p, data.get(p, ''))

        org.save()

        return org


class OrganizationCollaboration(Resource):
    """Collaborations for a specific organization."""

    @jwt_required
    def get(self, id):
        organization = db.Organization.get(id)
        return organization.collaborations

    @jwt_required
    def post(self, id):
        data = request.get_json()
        organization = db.Organization.get(id)
        collaboration = db.Collaboration.get(data['id'])
        organization.collaborations.append(collaboration)
        organization.save()
        return organization.collaborations


class OrganizationNode(Resource):
    """Resource for /api/organization/<int:id>/node."""

    @jwt_required
    def get(self, id, node_id=None):
        """Return a list of Nodes."""
        organization = db.Organization.get(id)

        if node_id is not None:
            node = db.Node.get(node_id)
            if node in organization.nodes:
                return node

        return organization.nodes     

    @jwt_required
    def post(self, id):
        """Create new node"""
        data = request.get_json()
        data['id'] = id
        node = db.Node.fromDict(data)
        node.save()

        return node


