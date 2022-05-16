# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flasgger import swag_from
from pathlib import Path

from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server.model import Rule as db_Rule
from vantage6.server.resource._schema import RuleSchema


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

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
# Resources / API's
# ------------------------------------------------------------------------------
class Rule(ServicesResources):

    rule_schema = RuleSchema()

    @with_user
    @swag_from(str(Path(r"swagger/get_rule_with_id.yaml")),
               endpoint='rule_with_id')
    @swag_from(str(Path(r"swagger/get_rule_without_id.yaml")),
               endpoint='rule_without_id')
    def get(self, id=None):
        """List rules."""

        rules = db_Rule.get(id)
        if id and not rules:
            return {'msg': f'Rule id={id} not found!'}, HTTPStatus.NOT_FOUND

        return self.rule_schema.dump(rules, many=not id).data,\
            HTTPStatus.OK
