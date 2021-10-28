# -*- coding: utf-8 -*-
import logging

from flask import request, g
from flask_restful import reqparse
from flasgger import swag_from
from http import HTTPStatus
from pathlib import Path

from vantage6.server import db
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
        Collaboration,
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
class Collaboration(ServicesResources):

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(['user', 'node', 'container'])
    @swag_from(str(Path(r"swagger/get_collaboration_with_id.yaml")),
               endpoint='collaboration_with_id')
    @swag_from(str(Path(r"swagger/get_collaboration_without_id.yaml")),
               endpoint='collaboration_without_id')
    def get(self, id=None):
        """collaboration or list of collaborations in case no id is provided"""
        collaboration = db.Collaboration.get(id)

        # check that collaboration exists, unlikely to happen without ID
        if not collaboration:
            return {"msg": f"collaboration having id={id} not found"},\
                HTTPStatus.NOT_FOUND

        if g.user:
            auth_org_id = g.user.organization.id
        elif g.node:
            auth_org_id = g.node.organization.id
        else:  # g.container
            auth_org_id = g.container["organization_id"]

        if id:

            # verify that the user/node organization is within the
            # collaboration
            ids = [org.id for org in collaboration.organizations]
            if not self.r.v_glo.can():
                if not (self.r.v_org.can() and auth_org_id in ids):
                    return {'msg': 'You lack the permission to do that!'}, \
                        HTTPStatus.UNAUTHORIZED

            return collaboration_schema.dump(collaboration, many=False).data, \
                HTTPStatus.OK  # 200

        else:
            if self.r.v_glo.can():
                allowed_collaborations = collaboration

            elif self.r.v_org.can():
                allowed_collaborations = []
                for col in collaboration:
                    if auth_org_id in [org.id for org in col.organizations]:
                        allowed_collaborations.append(col)

            return collaboration_schema.dump(collaboration, many=True)\
                .data, HTTPStatus.OK  # 200

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

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @only_for(["node", "user", "container"])
    @swag_from(str(Path(r"swagger/get_collaboration_organization.yaml")),
               endpoint='collaboration_with_id_organization')
    def get(self, id):
        """Return organizations for a specific collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration having collaboration_id={id} can "
                    "not be found"}, HTTPStatus.NOT_FOUND

        if g.user:
            auth_org_id = g.user.organization.id
        elif g.node:
            auth_org_id = g.node.organization.id
        else:  # g.container
            auth_org_id = g.container["organization_id"]

        if not self.r.v_glo.can():
            org_ids = [org.id for org in collaboration.organizations]
            if not (self.r.v_org.can() and auth_org_id in org_ids):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return org_schema.dump(collaboration.organizations, many=True).data, \
            HTTPStatus.OK

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

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, module_name)

    @with_user
    @swag_from(str(Path(r"swagger/get_collaboration_with_id_node.yaml")),
               endpoint='collaboration_with_id_node')
    def get(self, id):
        """"Return a list of nodes that belong to the collaboration."""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration id={id} can not be found"},\
                HTTPStatus.NOT_FOUND

        if not self.r.v_glo.can():
            org_ids = [org.id for org in collaboration.organizations]
            if not (self.r.v_org.can() and g.user.organization.id in org_ids):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return node_schema.dump(collaboration.nodes, many=True).data, \
            HTTPStatus.OK

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

    def __init__(self, socketio, mail, api, permissions):
        super().__init__(socketio, mail, api, permissions)
        self.r = getattr(self.permissions, 'task')

    @with_user_or_node
    @swag_from(str(Path(r"swagger/get_collaboration_with_id_task.yaml")),
               endpoint='collaboration_with_id_task')
    def get(self, id):
        """List of tasks that belong to a collaboration"""
        collaboration = db.Collaboration.get(id)
        if not collaboration:
            return {"msg": f"collaboration id={id} can not be found"},\
                HTTPStatus.NOT_FOUND

        if g.user:
            auth_org_id = g.user.organization.id
        else:  # g.node:
            auth_org_id = g.node.organization.id

        if not self.r.v_glo.can():
            org_ids = [org.id for org in collaboration.organizations]
            if not (self.r.v_org.can() and auth_org_id in org_ids):
                return {'msg': 'You lack the permission to do that!'}, \
                    HTTPStatus.UNAUTHORIZED

        return tasks_schema.dump(collaboration.tasks, many=True).data, \
            HTTPStatus.OK
