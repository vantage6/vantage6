# -*- coding: utf-8 -*-
"""
Resources below '/<api_base>/role'
"""
import logging

from http import HTTPStatus
from flask.globals import request
from flask_restful import Resource, abort
from flasgger import swag_from
from pathlib import Path
from flask_principal import Permission
from flask_restful import reqparse

from vantage6.server.resource import with_user
from vantage6.common import logger_name
from vantage6.server.permission import (
    register_rule, valid_rule_need
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.model import Role as db_Role, Rule
from vantage6.server.model.base import Database
from vantage6.server.resource._schema import RoleSchema

from vantage6.server._version import __version__

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Role,
        path,
        endpoint='role_without_id',
        methods=('GET', 'POST')
    )
    api.add_resource(
        Role,
        path + '/<int:id>',
        endpoint="role_with_id",
        methods=('GET', 'PATCH', 'DELETE')
    )

# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------
# rule = register_rule(
#     "see version",
#     [Scope.GLOBAL],
#     [Operation.VIEW],
#     "Can you see the version or not?"
# )

# permission = rule(Scope.GLOBAL, Operation.VIEW)
# test_permission = Permission(permission)
# test_permission.description = "Can you see the version or not?"


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
class Role(Resource):

    role_schema = RoleSchema()

    @with_user
    @swag_from(str(Path(r"swagger/role_with_id.yaml")),
               endpoint='role_with_id')
    @swag_from(str(Path(r"swagger/role_without_id.yaml")),
               endpoint='role_without_id')
    def get(self, id=None):
        """List roles."""

        roles = db_Role.get(id)
        return self.role_schema.dump(roles, many=not id).data, HTTPStatus.OK

    @with_user
    def post(self):
        """Create new role."""
        parser = reqparse.RequestParser()
        parser.add_argument("name", type=str, required=True)
        parser.add_argument("description", type=str, required=True)
        parser.add_argument("rules", type=int, action='append', required=True)
        data = parser.parse_args()

        # obtain the requested rules from the DB
        rules = []
        for rule_id in data["rules"]:
            rule = Rule.get(rule_id)
            if not rule:
                return {"msg": f"Rule id={rule_id} not found."}, \
                    HTTPStatus.BAD_REQUEST
            rules.append(rule)

        # check if all fields are present
        role = db_Role(name=data["name"], description=data["description"],
                       rules=rules)
        role.save()
        return self.role_schema.dump(role, many=False).data, HTTPStatus.CREATED

    def patch(self, id):
        """Update role."""
        data = request.get_json()
        role = db_Role.get(id)
        if not role:
            return {"msg": "Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        if 'name' in data:
            role.name = data["name"]
        if 'description' in data:
            role.description = data["description"]

        role.save()

        return self.role_schema.dump(role, many=False).data, HTTPStatus.CREATED

    def delete(self, id):
        role = db_Role.get(id)
        if not role:
            return {"msg": f"Role with id={id} not found."}, \
                HTTPStatus.NOT_FOUND

        role.delete()
        return {"msg": "Role removed from the database."}, HTTPStatus.OK
