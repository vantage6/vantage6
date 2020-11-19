# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/role'
"""
import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import Resource
from flasgger import swag_from
from pathlib import Path
from flask_restful import reqparse

from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server.permission import (
    register_rule,
    verify_user_rules
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.model import Role as db_Role, Rule, Organization
from vantage6.server.resource._schema import RoleSchema, RuleSchema


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Role,
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
        methods=('POST', 'DELETE'),
        resource_class_kwargs=services
    )


# -----------------------------------------------------------------------------
# Permissions
# -----------------------------------------------------------------------------
role_permission = register_rule(
    "manage_roles",
    [Scope.ORGANIZATION, Scope.GLOBAL],
    [Operation.VIEW, Operation.EDIT, Operation.CREATE, Operation.DELETE],
    "Manage roles"
)

# VIEW  / GET
view_any = role_permission(Scope.GLOBAL, Operation.VIEW)
view_any.description = "View any role at the server"
view_organization = role_permission(Scope.ORGANIZATION, Operation.VIEW)
view_organization.description = "View the roles of your organization"

# CREATE / POST
create_any = role_permission(Scope.GLOBAL, Operation.CREATE)
create_any.description = "Create a role of any organization"
create_organization = role_permission(Scope.ORGANIZATION, Operation.CREATE)
create_organization.description = "Create a new role for your organization"

# EDIT / PATCH
edit_any = role_permission(Scope.GLOBAL, Operation.EDIT)
edit_any.description = "Edit any role"
edit_organization = role_permission(Scope.ORGANIZATION, Operation.EDIT)
edit_organization.description = "Edit a role within your organization"

delete_any = role_permission(Scope.GLOBAL, Operation.DELETE)
delete_organization = role_permission(Scope.ORGANIZATION, Operation.DELETE)


# -----------------------------------------------------------------------------
# Resources / API's
# -----------------------------------------------------------------------------
class Role(ServicesResources):

    role_schema = RoleSchema()

    @with_user
    @swag_from(str(Path(r"swagger/get_role_with_id.yaml")),
               endpoint='role_with_id')
    @swag_from(str(Path(r"swagger/get_role_without_id.yaml")),
               endpoint='role_without_id')
    def get(self, id=None):
        """View roles

        Depending on your permissions you see no, your organization or all
        available roles at the server.
        """
        if view_any.can():
            # view all roles at the server
            roles = db_Role.get(id)
        elif view_organization.can():
            # view all roles from your organization
            roles = [role for role in db_Role.get(id)
                     if role.organization == g.user.organization]
        else:
            return {"msg": "You do not have permission to view this."}, \
                HTTPStatus.UNAUTHORIZED

        return self.role_schema.dump(roles, many=not id).data, HTTPStatus.OK

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
        parser.add_argument("rules", type=int, action='append', required=True)
        parser.add_argument("organization_id", type=int, required=False)
        data = parser.parse_args()

        # obtain the requested rules from the DB.
        rules = []
        for rule_id in data["rules"]:
            rule = Rule.get(rule_id)
            if not rule:
                return {"msg": f"Rule id={rule_id} not found."}, \
                    HTTPStatus.BAD_REQUEST
            rules.append(rule)

        # And check that this used has the rules he is trying to assign
        denied = verify_user_rules(rules)
        if denied:
            return denied, HTTPStatus.UNAUTHORIZED

        # if trying to create a role for another organization
        if data["organization_id"] and not create_any.can():
            return {'msg': 'You cannot create roles for other organizations'},\
                HTTPStatus.UNAUTHORIZED
        elif data["organization_id"] and create_any.can():
            organization_id = data["organization_id"]

            # verify that the organization exists
            if not Organization.get(organization_id):
                return {'msg': f'organization "{organization_id}" does not '
                        'exist!'}, HTTPStatus.NOT_FOUND
        elif (not data['organization_id'] and create_any.can()) or \
                create_organization.can():
            organization_id = g.user.organization_id
        else:
            return {'msg': 'You lack the permission to create roles!'}, \
                HTTPStatus.UNAUTHORIZED

        # create the actual role
        role = db_Role(name=data["name"], description=data["description"],
                       rules=rules, organization_id=organization_id)
        role.save()

        return self.role_schema.dump(role, many=False).data, HTTPStatus.CREATED

    @with_user
    @swag_from(str(Path(r"swagger/patch_role_with_id.yaml")),
               endpoint='role_with_id')
    def patch(self, id):
        """Update role."""
        data = request.get_json()

        role = db_Role.get(id)
        if not role:
            return {"msg": "Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        # check permission of the user
        if not edit_any.can():
            if not edit_organization.can():
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
                rule = Rule.get(rule_id)
                if not rule:
                    return {'msg': f'rule with id={rule_id} not found!'}, \
                        HTTPStatus.NOT_FOUND
                rules.append(rule)
            denied = verify_user_rules(rules)
            if denied:
                return denied, HTTPStatus.UNAUTHORIZED
            role.rules = rules
        role.save()

        return self.role_schema.dump(role, many=False).data, HTTPStatus.OK

    @with_user
    @swag_from(str(Path(r"swagger/delete_role_with_id.yaml")),
               endpoint='role_with_id')
    def delete(self, id):

        role = db_Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        if not delete_any.can():
            if not delete_organization.can():
                return {'msg': 'You do not have permission to delete roles!'},\
                    HTTPStatus.UNAUTHORIZED
            elif role.organization.id != g.user.organization.id:
                return {'msg': 'You can\'t delete a role from another '
                        'organization'}, HTTPStatus.UNAUTHORIZED

        role.delete()

        return {"msg": "Role removed from the database."}, HTTPStatus.OK


class RoleRules(ServicesResources):

    rule_schema = RuleSchema()

    def get(self, id):
        role = Role.get(id)
        if not role:
            return {'msg', f'Role id={id} not found!'}, HTTPStatus.NOT_FOUND

        rules = role.rules
        return self.rule_schema.dump(rules, many=False).data, HTTPStatus.OK

    def post(self, id, rule_id):
        rule = Rule.get(rule_id)
        if not rule:
            return {'msg': f'Rule id={rule_id} not found'}, \
                HTTPStatus.NOT_FOUND

    def delete(self, id, rule_id):
        pass
