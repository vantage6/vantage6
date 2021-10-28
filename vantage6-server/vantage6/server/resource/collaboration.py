# -*- coding: utf-8 -*-
import logging

from flask import request
from flask_restful import reqparse
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6.server import db
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.resource.pagination import Pagination
from vantage6.server.permission import (
    Scope as S,
    Operation as P,
    PermissionManager
)
from vantage6.server.resource._schema import (
    CollaborationSchema,
    TaskSchema,
    OrganizationSchema,
    NodeSchemaSimple
)
from vantage6.server.resource import (
    with_user_or_node,
    with_user,
    only_for,
    ServicesResources
)


module_name = __name__.split('.')[-1]
log = logging.getLogger(module_name)


def setup(api, api_base, services):
    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Collaborations,
        path,
        endpoint='collaboration_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Collaboration,
        path + '/<int:id>',
        endpoint='collaboration_with_id',
        methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        CollaborationOrganization,
        path+'/<int:id>/organization',
        endpoint='collaboration_with_id_organization',
        methods=('GET', 'POST', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        CollaborationNode,
        path+'/<int:id>/node',
        endpoint='collaboration_with_id_node',
        methods=('GET', 'POST', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        CollaborationTask,
        path+'/<int:id>/task',
        endpoint='collaboration_with_id_task',
        methods=('GET',),
        resource_class_kwargs=services
    )


# Schemas
collaboration_schema = CollaborationSchema()
tasks_schema = TaskSchema()
org_schema = OrganizationSchema()
node_schema = NodeSchemaSimple()


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permissions: PermissionManager):

    add = permissions.appender(module_name)

    add(scope=S.GLOBAL, operation=P.VIEW,
        description="view any collaboration")

    add(scope=S.ORGANIZATION, operation=P.VIEW, assign_to_container=True,
        assign_to_node=True,
        description="view collaborations of your organization")

    add(scope=S.GLOBAL, operation=P.EDIT,
        description="edit any collaboration")

    add(scope=S.GLOBAL, operation=P.CREATE,
        description="create a new collaboration")

    add(scope=S.GLOBAL, operation=P.DELETE,
        description="delete a collaboration")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class CollaborationBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Collaborations(CollaborationBase):

    @with_user
    def get(self):
        """Returns a list of collaborations
        ---

        description: >-
            Returns a list of collaborations. Depending on your permission, all
            collaborations are shown or only collaborations in which your
            organization participates. See the table bellow.\n\n

            ### Permission Table\n
            |Rulename|Scope|Operation|Node|Container|Description|\n
            | -- | -- | -- | -- | -- | -- |\n
            |Collaboration|Global|View|❌|❌|All collaborations|\n
            |Collaboration|Organization|View|✅|✅|Collaborations in which
            your organization participates |\n\n

            Accessable as: `user`.'\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

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
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Collaboration"]
        """

        # obtain organization from authenticated
        auth_org_id = self.obtain_organization_id()
        q = DatabaseSessionManager.get_session().query(db.Collaboration)

        # filter based on permissions
        if not self.r.v_glo.can():
            if self.r.v_org.can():
                q = q.join(db.Organization, db.Collaboration.organizations)\
                    .filter(db.Collaboration.organizations.any(id=auth_org_id))
            else:
                return {'msg': 'You lack the permission to do that!'}

        # paginate the results
        page = Pagination.from_query(query=q, request=request)

        # serialize models, include metadata if requested
        return self.response(page, collaboration_schema)

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_without_id.yaml")),
               endpoint='collaboration_without_id')
    def post(self):
        """create a new collaboration"""

        parser = reqparse.RequestParser()
        parser.add_argument('name', type=str, required=True,
                            help="This field cannot be left blank!")
        parser.add_argument('organization_ids', type=int, required=True,
                            action='append')
        parser.add_argument('encrypted', type=int, required=False)
        data = parser.parse_args()

        name = data["name"]
        if db.Collaboration.name_exists(name):
            return {"msg": f"Collaboration name '{name}' already exists!"}, \
                HTTPStatus.BAD_REQUEST

        if not self.r.c_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        encrypted = True if data["encrypted"] == 1 else False

        collaboration = db.Collaboration(
            name=name,
            organizations=[
                db.Organization.get(org_id)
                for org_id in data['organization_ids']
                if db.Organization.get(org_id)
            ],
            encrypted=encrypted
        )

        collaboration.save()
        return collaboration_schema.dump(collaboration).data, HTTPStatus.OK


class Collaboration(CollaborationBase):

    @only_for(['user', 'node', 'container'])
    @swag_from(str(Path(r"swagger/get_collaboration_with_id.yaml")),
               endpoint='collaboration_with_id')
    def get(self, id):
        """collaboration or list of collaborations in case no id is provided"""
        collaboration = db.Collaboration.get(id)

        # check that collaboration exists, unlikely to happen without ID
        if not collaboration:
            return {"msg": f"collaboration having id={id} not found"},\
                HTTPStatus.NOT_FOUND

        # obtain the organization id of the authenticated
        auth_org_id = self.obtain_organization_id()

        # verify that the user/node organization is within the
        # collaboration
        ids = [org.id for org in collaboration.organizations]
        if not self.r.v_glo.can():
            if not (self.r.v_org.can() and auth_org_id in ids):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return collaboration_schema.dump(collaboration, many=False).data, \
            HTTPStatus.OK  # 200

    @with_user
    @swag_from(str(Path(r"swagger/patch_collaboration_with_id.yaml")),
               endpoint='collaboration_with_id')
    def patch(self, id):
        """update a collaboration"""

        collaboration = db.Collaboration.get(id)

        # check if collaboration exists
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} "
                    "can not be found"}, HTTPStatus.NOT_FOUND  # 404

        # verify permissions
        if not self.r.e_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # only update fields that are provided
        data = request.get_json()
        if "name" in data:
            collaboration.name = data["name"]
        if "organization_ids" in data:
            collaboration.organizations = [
                db.Organization.get(org_id)
                for org_id in data['organization_ids']
                if db.Organization.get(org_id)
            ]
        if 'encrypted' in data:
            collaboration.encrypted = data['encrypted']

        collaboration.save()

        return collaboration_schema.dump(collaboration, many=False).data, \
            HTTPStatus.OK  # 200

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_with_id.yaml")),
               endpoint='collaboration_with_id')
    def delete(self, id):
        """delete collaboration"""

        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration id={id} is not found"}, \
                HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r.d_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        collaboration.delete()
        return {"msg": f"node id={id} successfully deleted"}, \
            HTTPStatus.OK


class CollaborationOrganization(ServicesResources):
    """Resource for /api/collaboration/<int:id>/organization."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)

    @only_for(["node", "user", "container"])
    def get(self, id):
        """Returns organizations that participate in the collaboration
        ---
        description: >-
            Returns a list of all organizations that belong to the specified
            collaboration.

            ### Permission Table\n
            |Rulename|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Collaboration|Global|View|❌|❌|All collaborations|\n
            |Collaboration|Organization|View|✅|✅|Collaborations
            in which your organization participates|\n\n

            Accessable as: `user`, `node` and `container`.'\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              description: collaboration id
              required: true
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
            404:
                description: Collaboration specified by id does not exists
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Collaboration"]
        """
        col = db.Collaboration.get(id)
        if not col:
            return {'msg': f'collaboration (id={id}) can not be found'},\
                HTTPStatus.NOT_FOUND

        # check permission
        if not self.r.v_glo.can():
            auth_org = self.obtain_auth_organization()
            if not (self.r.v_org.can() and auth_org in col.organizations):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate organizations
        page = Pagination.from_list(col.organizations, request)

        # model serialization
        return self.response(page, org_schema)

    @with_user
    @swag_from(
        str(Path(r"swagger/post_collaboration_with_id_organization.yaml")),
        endpoint='collaboration_with_id_organization'
    )
    def post(self, id):
        """Add an organizations to a specific collaboration."""
        # get collaboration to which te organization should be added
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} can "
                    "not be found"}, HTTPStatus.NOT_FOUND

        # verify permissions
        if not self.r.e_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # get the organization
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": f"organization with id={id} is not found"}, \
                HTTPStatus.NOT_FOUND

        # append organization to the collaboration
        collaboration.organizations.append(organization)
        collaboration.save()
        return org_schema.dump(collaboration.organizations, many=True).data, \
            HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_organization.yaml")),
               endpoint='collaboration_with_id_organization')
    def delete(self, id):
        """Removes an organization from a collaboration."""
        # get collaboration from which organization should be removed
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} can "
                    "not be found"}, HTTPStatus.NOT_FOUND

        # get organization which should be deleted
        data = request.get_json()
        organization = db.Organization.get(data['id'])
        if not organization:
            return {"msg": f"organization with id={id} is not found"}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        # delete organization and update
        collaboration.organizations.remove(organization)
        collaboration.save()
        return org_schema.dump(collaboration.organizations, many=True).data, \
            HTTPStatus.OK


class CollaborationNode(ServicesResources):
    """Resource for /api/collaboration/<int:id>/node."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)

    @with_user
    def get(self, id):
        """List nodes in collaboration.
        ---
        description: >-
            Returns a list of node(s) which belong to the specified
            collaboration.\n\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Collaboration|Global|View|❌|❌|List nodes in a specified
            collaboration|\n
            |Collaboration|Organization|View|✅|✅|List nodes in a specified
            collaboration|\n\n

            Accessable as: `user`.'\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              description: collaboration id
              required: true
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
            404:
                description: collaboration not found
            401:
                description: Unauthorized

        tags: ["Collaboration"]
        """
        col = db.Collaboration.get(id)
        if not col:
            return {"msg": f"collaboration id={id} can not be found"},\
                HTTPStatus.NOT_FOUND

        # check permission
        if not self.r.v_glo.can():
            auth_org = self.obtain_auth_organization()
            if not (self.r.v_org.can() and auth_org in col.organizations):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate nodes
        page = Pagination.from_list(col.nodes, request)

        # model serialization
        return self.response(page, node_schema)

    @with_user
    @swag_from(str(Path(r"swagger/post_collaboration_with_id_node.yaml")),
               endpoint='collaboration_with_id_node')
    def post(self, id):
        """Add an node to a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} can "
                    "not be found"}, HTTPStatus.NOT_FOUND

        if not self.r.e_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        node = db.Node.get(data['id'])
        if not node:
            return {"msg": f"node id={data['id']} not found"}, \
                HTTPStatus.NOT_FOUND
        if node in collaboration.nodes:
            return {"msg": f"node id={data['id']} is already in collaboration "
                    f"id={id}"}, HTTPStatus.BAD_REQUEST

        collaboration.nodes.append(node)
        collaboration.save()
        return node_schema.dump(collaboration.nodes, many=True).data,\
            HTTPStatus.CREATED

    @with_user
    @swag_from(str(Path(r"swagger/delete_collaboration_with_id_node.yaml")),
               endpoint='collaboration_with_id_node')
    def delete(self, id):
        """Remove node from collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} can "
                    "not be found"}, HTTPStatus.NOT_FOUND

        if not self.r.e_glo.can():
            return {'msg': 'You lack the permission to do that!'}, \
                HTTPStatus.UNAUTHORIZED

        data = request.get_json()
        node = db.Node.get(data['id'])
        if not node:
            return {"msg": f"node id={id} not found"}, HTTPStatus.NOT_FOUND
        if node not in collaboration.nodes:
            return {"msg": f"node id={data['id']} is not part of "
                    f"collaboration id={id}"}, HTTPStatus.BAD_REQUEST

        collaboration.nodes.remove(node)
        collaboration.save()
        return {"msg": f"node id={data['id']} removed from collaboration "
                f"id={id}"}, HTTPStatus.OK


class CollaborationTask(ServicesResources):
    """Resource for /api/collaboration/<int:id>/task."""

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, 'task')

    @with_user_or_node
    def get(self, id):
        """List tasks from collaboration
        ---
        description: >-
            Returns a list of all tasks that belong to the collaboration.\n\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Task|Global|View|❌|❌|View tasks|\n
            |Task|Organization|View|✅|✅|View tasks only when your
            organization participates in the collaboration|\n\n


            Accessible as: `user` and `node`.\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.


        parameters:
            - in: path
              name: id
              schema:
                type: integer
              description: collaboration id
              required: true
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
            404:
                description: Collaboration not found

        security:
            - bearerAuth: []

        tags: ["Collaboration"]

        """
        col = db.Collaboration.get(id)
        if not col:
            return {"msg": f"collaboration id={id} can not be found"},\
                HTTPStatus.NOT_FOUND

        # obtain auth's organization id
        auth_org = self.obtain_auth_organization()

        if not self.r.v_glo.can():
            if not (self.r.v_org.can() and auth_org in col.organizations):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate tasks
        page = Pagination.from_list(col.tasks, request)

        # model serialization
        return self.response(page, tasks_schema)
