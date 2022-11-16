# -*- coding: utf-8 -*-
import logging

from flask import request, g
from http import HTTPStatus

from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.resource.pagination import Pagination
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager
)
from vantage6.server.resource import (
    with_user_or_node, only_for, with_user, ServicesResources
)
from vantage6.server.resource.common._schema import (
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
        Organizations,
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
org_schema = OrganizationSchema()


class OrganizationBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Organizations(OrganizationBase):

    @only_for(["user", "node", "container"])
    def get(self):
        """ Returns a list organizations
        ---
        description: >-
            Get a list of organizations based on filters and user permissions\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Assigned to node|Assigned to container|
            Description|\n
            |--|--|--|--|--|--|\n
            |Organization|Global|View|❌|❌|View all organizations|\n
            |Organization|Collaboration|View|✅|✅|View a list of organizations
            within the scope of the collaboration|\n
            |Organization|Organization|View|✅|✅|View a 'list' of just the
            organization you are part of|\n

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
            name: country
            schema:
              type: string
            description: Country
          - in: query
            name: collaboration_id
            schema:
              type: integer
            description: Collaboration id
          - in: query
            name: include
            schema:
              type: string (can be multiple)
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

        tags: ["Organization"]
        """

        # Obtain the organization of the requester
        auth_org = self.obtain_auth_organization()
        args = request.args

        # query
        q = g.session.query(db.Organization)

        # filter by a field of this endpoint
        if 'name' in args:
            q = q.filter(db.Organization.name.like(args['name']))
        if 'country' in args:
            q = q.filter(db.Organization.country == args['country'])
        if 'collaboration_id' in args:
            q = q.join(db.Member).join(db.Collaboration)\
                 .filter(db.Collaboration.id == args['collaboration_id'])

        # filter the list of organizations based on the scope
        if self.r.v_glo.can():
            pass  # don't apply filters
        elif self.r.v_col.can():
            # obtain collaborations your organization participates in
            collabs = g.session.query(db.Collaboration).filter(
                db.Collaboration.organizations.any(id=auth_org.id)
            ).all()

            # list comprehension fetish, and add own organization in case
            # this organization does not participate in any collaborations yet
            org_ids = [o.id for col in collabs for o in col.organizations]
            org_ids = list(set(org_ids + [auth_org.id]))

            # select only the organizations in the collaborations
            q = q.filter(db.Organization.id.in_(org_ids))

        elif self.r.v_org.can():
            q = q.filter(db.Organization.id == auth_org.id)
        else:
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # paginate the results
        page = Pagination.from_query(query=q, request=request)

        # serialization of DB model
        return self.response(page, org_schema)

    @with_user
    def post(self):
        """Create new organization
        ---
        description: >-
          Creates a new organization from the specified values\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Organization|Global|Create|❌|❌|Create a new organization|\n

          Accessible to users.

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Organization'

        responses:
          201:
            description: Ok
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Organization"]
        """

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

        return org_schema.dump(organization, many=False).data, \
            HTTPStatus.CREATED


class Organization(OrganizationBase):

    @only_for(["user", "node", "container"])
    def get(self, id):
        """Get organization
        ---
        description: >-
          Returns the organization specified by the id\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Organization|Global|View|❌|❌|View all organizations|\n
          |Organization|Collaboration|View|✅|✅|View a list of organizations
          within the scope of the collaboration|\n
          |Organization|Organization|View|✅|✅|View a list of organizations
          that the user is part of|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Organization id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Organization not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Organization"]
        """

        # obtain organization of authenticated
        auth_org = self.obtain_auth_organization()

        # retrieve requested organization
        req_org = db.Organization.get(id)
        if not req_org:
            return {'msg': f'Organization id={id} not found!'}, \
                HTTPStatus.NOT_FOUND

        accepted = False
        # Check if auth has enough permissions
        if self.r.v_glo.can():
            accepted = True
        elif self.r.v_col.can():
            # check if the organization is whithin a collaboration
            for col in auth_org.collaborations:
                if req_org in col.organizations:
                    accepted = True
            # or that the organization is auths org
            if req_org == auth_org:
                accepted = True
        elif self.r.v_org.can():
            accepted = auth_org == req_org

        if accepted:
            return org_schema.dump(req_org, many=False).data, \
                HTTPStatus.OK
        else:
            return {'msg': 'You do not have permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

    @only_for(["user", "node"])
    def patch(self, id):
        """Update organization
        ---
        description: >-
          Updates the organization with the specified id.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Organization|Global|Edit|❌|❌|Update an organization with
          specified id|\n
          |Organization|Organization|Edit|❌|❌|Update the organization that
          the user is part of|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Organization id
            required: tr

        requestBody:
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Organization'

        responses:
          200:
            description: Ok
          404:
            description: Organization with specified id is not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Organization"]
        """

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
            if field in data and data[field] is not None:
                setattr(organization, field, data[field])

        organization.save()
        return org_schema.dump(organization, many=False).data, \
            HTTPStatus.OK


class OrganizationCollaboration(ServicesResources):
    """Collaborations for a specific organization."""

    col_schema = CollaborationSchema()

    @only_for(["user", "node"])
    def get(self, id):
        """Get collaborations from organization
        ---
        description: >-
          Returns a list of collaborations in which the organization is a
          participant of.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Collaboration|Global|View|❌|❌|View all collaborations|\n
          |Collaboration|Organization|View|✅|✅|View a list of collaborations
          that the organization is a part of|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Organization id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Organization not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Organization"]
        """
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
    def get(self, id):
        """Return a list of nodes.
        ---
        description: >-
          Returns a list of nodes which are from the organization.\n

          ### Permission Table\n
          |Rule name|Scope|Operation|Assigned to node|Assigned to container|
          Description|\n
          |--|--|--|--|--|--|\n
          |Organization|Global|View|❌|❌|View any node|\n
          |Organization|Organization|View|✅|✅|View a list of nodes that
          belong to your organization|\n

          Accessible to users.

        parameters:
          - in: path
            name: id
            schema:
              type: integer
            description: Organization id
            required: true

        responses:
          200:
            description: Ok
          404:
            description: Organization not found
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Organization"]
        """
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
