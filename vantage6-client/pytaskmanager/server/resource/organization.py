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

from . import with_user_or_client, with_client
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
    api.add_resource(OrganizationClient,
        path + '/<int:id>/client',
        path + '/<int:id>/client/<int:client_id>',
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


class OrganizationClient(Resource):
    """Resource for /api/organization/<int:id>/client."""

    @jwt_required
    def get(self, id, client_id=None):
        """Return a list of Clients."""
        organization = db.Organization.get(id)

        if client_id is not None:
            client = db.Client.get(client_id)
            if client in organization.clients:
                return client

        return organization.clients     

    @jwt_required
    def post(self, id):
        """Create new client"""
        data = request.get_json()
        data['id'] = id
        client = db.Client.fromDict(data)
        client.save()

        return client


