# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flasgger import swag_from
from pathlib import Path
from flask_restful import reqparse
from vantage6.server import db
from vantage6.server.model.base import DatabaseSessionManager

from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server.permission import (
    PermissionManager
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.resource._schema import RoleSchema, RuleSchema
from vantage6.server.resource.pagination import Pagination

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Roles,
        path,
        endpoint='role_without_id',
        methods=('GET', 'POST'),
        resource_class_kwargs=services
    )
    api.add_resource(
        Role,
        path + '/<int:id>',
        endpoint="role_with_id",
        methods=('GET', 'PATCH', 'DELETE'),
        resource_class_kwargs=services
    )
    api.add_resource(
        RoleRules,
        path + '/<int:id>/rule',
        endpoint='role_rule_without_id',
        methods=('GET',),
        resource_class_kwargs=services
    )
    api.add_resource(
        RoleRules,
        path + '/<int:id>/rule/<int:rule_id>',
        endpoint='role_rule_with_id',
        methods=('GET', 'DELETE', 'POST'),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
def permissions(permission: PermissionManager):
    add = permission.appender(module_name)
    add(scope=Scope.GLOBAL, operation=Operation.VIEW,
        description="View any role")
    add(scope=Scope.ORGANIZATION, operation=Operation.VIEW,
        description="View the roles of your organization")
    add(scope=Scope.GLOBAL, operation=Operation.CREATE,
        description="Create role for any organization")
    add(scope=Scope.ORGANIZATION, operation=Operation.CREATE,
        description="Create role for your organization")
    add(scope=Scope.GLOBAL, operation=Operation.EDIT,
        description="Edit any role")
    add(scope=Scope.ORGANIZATION, operation=Operation.EDIT,
        description="Edit a role from your organization")
    add(scope=Scope.GLOBAL, operation=Operation.DELETE,
        description="Delete any organization")
    add(scope=Scope.ORGANIZATION, operation=Operation.DELETE,
        description="Delete your organization")


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
role_schema = RoleSchema()
rule_schema = RuleSchema()


class RoleBase(ServicesResources):

    def __init__(self, socketio, mail, api, permissions, config):
        super().__init__(socketio, mail, api, permissions, config)
        self.r = getattr(self.permissions, module_name)


class Roles(RoleBase):

    @with_user
    def get(self):
        """Returns a list of roles
        ---

        description: >-
            Returns a list of roles. Depending on your permission, you get all
            the roles at the server or only the roles that belong to your
            organization.\n\n

            ### Permission Table\n
            |Rulename|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Role|Global|View|❌|❌|View all roles|\n
            |Role|Organization|View|❌|❌|View roles that are part of your
            organization|\n\n

            Accesible for: `user`.\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

        parameters:
            - in: query
              name: include
              schema:
                type: string (can be multiple)
              description: what to include ('metadata')
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

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        q = DatabaseSessionManager.get_session().query(db.Role)

        auth_org_id = self.obtain_organization_id()

        if not self.r.v_glo.can():
            if self.r.v_org.can():
                q = q.join(db.Organization)\
                    .filter(db.Role.organization_id == auth_org_id)
            else:
                return {"msg": "You do not have permission to view this."}, \
                    HTTPStatus.UNAUTHORIZED

        page = Pagination.from_query(query=q, request=request)

        return self.response(page, role_schema)

    @with_user
    @swag_from(str(Path(r"swagger/post_role_without_id.yaml")),
               endpoint='role_without_id')
    def post(self):
        """Create a new role

        You can only assign rules that you own. You need permission to create
        roles, and you can only assign roles to other organizations if you
        have gobal permission.

        """
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True)
        parser.add_argument("description", type=str, required=True)
        parser.add_argument("rules", type=int, action='append', required=False)
        parser.add_argument("organization_id", type=int, required=False)
        data = parser.parse_args()

        # obtain the requested rules from the DB.
        rules = []
        if data['rules']:
            for rule_id in data["rules"]:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {"msg": f"Rule id={rule_id} not found."}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)

        # And check that this used has the rules he is trying to assign
        denied = self.permissions.verify_user_rules(rules)
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        # set the organization id
        organization_id = (
            data['organization_id']
            if data['organization_id'] else g.user.organization_id
        )
        # verify that the organization for which we create a role exists
        if not db.Organization.get(organization_id):
            return {'msg': f'organization "{organization_id}" does not '
                    'exist!'}, HTTPStatus.NOT_FOUND

        # check if user is allowed to create this role
        if (not self.r.c_glo.can() and
                organization_id != g.user.organization_id):
            return {
                'msg': 'You cannot create roles for other organizations!'
            }, HTTPStatus.UNAUTHORIZED
        elif not self.r.c_glo.can() and not self.r.c_org.can():
            return {'msg': 'You lack the permission to create roles!'}, \
                HTTPStatus.UNAUTHORIZED

        # create the actual role
        role = db.Role(name=data["name"], description=data["description"],
                       rules=rules, organization_id=organization_id)
        role.save()

        return role_schema.dump(role, many=False).data, HTTPStatus.CREATED


class Role(RoleBase):

    @with_user
    @swag_from(str(Path(r"swagger/get_role_with_id.yaml")),
               endpoint='role_with_id')
    def get(self, id):
        role = db.Role.get(id)

        # check permissions
        if not self.r.v_glo.can():
            if not (self.r.v_org.can()
                    and role.organization == g.user.organization):
                return {"msg": "You do not have permission to view this."},\
                     HTTPStatus.UNAUTHORIZED

        return role_schema.dump(role, many=False).data, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/patch_role_with_id.yaml")),
               endpoint='role_with_id')
    def patch(self, id):
        """Update role."""
        data = request.get_json()

        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        # check permission of the user
        if not self.r.e_glo.can():
            if not self.r.e_org.can():
                return {'msg': 'You do not have permission to edit roles!'}, \
                    HTTPStatus.UNAUTHORIZED
            elif g.user.organization_id != role.organization.id:
                return {'msg': 'You can\'t edit roles from another '
                        'organization'}, HTTPStatus.UNAUTHORIZED

        # process patch
        if 'name' in data:
            role.name = data["name"]
        if 'description' in data:
            role.description = data["description"]
        if 'rules' in data:
            rules = []
            for rule_id in data['rules']:
                rule = db.Rule.get(rule_id)
                if not rule:
                    return {'msg': f'rule with id={rule_id} not found!'}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)
            denied = self.permissions.verify_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED
            role.rules = rules
        role.save()

        return role_schema.dump(role, many=False).data, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_role_with_id.yaml")),
               endpoint='role_with_id')
    def delete(self, id):

        role = db.Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            if not self.r.d_org.can():
                return {'msg': 'You do not have permission to delete roles!'},\
                    HTTPStatus.UNAUTHORIZED
            elif role.organization.id != g.user.organization.id:
                return {'msg': 'You can\'t delete a role from another '
                        'organization'}, HTTPStatus.UNAUTHORIZED

        role.delete()

        return {"msg": "Role removed from the database."}, HTTPStatus.OK


class RoleRules(RoleBase):

    @with_user
    def get(self, id):
        """Returns the rules for a specific role
        ---
        description: >-
            View the rules that belong to a specific role.\n\n

            ### Permission Table\n
            |Rule name|Scope|Operation|Node|Container|Description|\n
            |--|--|--|--|--|--|\n
            |Role|Global|View|❌|❌|View any role rule|\n
            |Role|Organization|View|❌|❌|View all role rules in your
            organization|\n\n

            Accessible for: `user`\n\n

            Results can be paginated by using the parameter `page`. The
            pagination metadata can be included using `include=metadata`, note
            that this will put the actual data in an envelope.

        parameters:
            - in: path
              name: id
              schema:
                type: integer
              minimum: 1
              description: Role id
              required: true
            - in: query
              name: include
              schema:
                 type: string (can be multiple)
              description: what to include ('task', 'metadata')
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
                description: Node with specified id is not found
            401:
                description: Unauthorized or missing permission

        security:
            - bearerAuth: []

        tags: ["Role"]
        """
        role = db.Role.get(id)

        if not role:
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND

        # obtain auth organization model
        auth_org = self.obtain_auth_organization()

        # check permission
        if not self.r.v_glo.can():
            if not (self.r.v_org.can() and auth_org == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # paginate elements
        page = Pagination.from_list(role.rules, request)

        return self.response(page, rule_schema)

    @with_user
    @swag_from(str(Path(r"swagger/post_role_rule_with_id.yaml")),
               endpoint='role_with_id')
    def post(self, id, rule_id):
        """Add rule to a role."""
        role = db.Role.get(id)
        if not role:
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND
        rule = db.Rule.get(rule_id)
        if not rule:
            return {'msg': f'Rule id={rule_id} not found!'}, \
                HTTPStatus.NOT_FOUND

        # check that this user can edit rules
        if not self.r.e_glo.can():
            if not (self.r.e_org.can() and
                    g.user.organization == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # user needs to role to assign it
        denied = self.permissions.verify_user_rules([rule])
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        # We're good, lets add the rule
        role.rules.append(rule)
        role.save()

        return rule_schema.dump(role.rules, many=False).data, \
            HTTPStatus.CREATED

    @with_user
    @swag_from(str(Path(r"swagger/delete_role_rule_with_id.yaml")),
               endpoint='role_rule_with_id')
    def delete(self, id, rule_id):
        """Remove rule from role."""
        role = db.Role.get(id)
        if not role:
            return {'msg': f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND
        rule = db.Rule.get(rule_id)
        if not rule:
            return {'msg': f'Rule id={rule_id} not found!'}, \
                HTTPStatus.NOT_FOUND

        if not self.r.d_glo.can():
            if not (self.r.d_org.can() and
                    g.user.organization == role.organization):
                return {'msg': 'You lack permissions to do that'}, \
                    HTTPStatus.UNAUTHORIZED

        # user needs to role to remove it
        denied = self.permissions.verify_user_rules([rule])
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        if not (rule in role.rules):
            return {'msg': f'Rule id={rule_id} not found in Role={id}!'}, \
                HTTPStatus.NOT_FOUND

        # Ok jumped all hoopes, remove it..
        role.rules.remove(rule)

        return rule_schema.dump(role.rules, many=False).data, \
            HTTPStatus.OK
