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

from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server.permission import (
    register_rule, valid_rule_need
)
from vantage6.server.model.rule import Operation, Scope
from vantage6.server.model import Rule as db_Rule
from vantage6.server.model.base import Database
from vantage6.server.resource._schema import RuleSchema

from vantage6.server._version import __version__

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info('Setting up "{}" and subdirectories'.format(path))

    api.add_resource(
        Rule,
        path,
        endpoint='rule_without_id',
        methods=('GET',),
        resource_class_kwargs=services
    )
    api.add_resource(
        Rule,
        path + '/<int:id>',
        endpoint='rule_with_id',
        methods=('GET',),
        resource_class_kwargs=services
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
class Rule(ServicesResources):

    rule_schema = RuleSchema()

    @with_user
    @swag_from(str(Path(r"swagger/rule_with_id.yaml")),
               endpoint='rule_with_id')
    @swag_from(str(Path(r"swagger/rule_without_id.yaml")),
               endpoint='rule_without_id')
    def get(self, id=None):
        """List rules."""

        roles = db_Rule.get(id)
        return self.rule_schema.dump(roles, many=not id).data,\
            HTTPStatus.OK
