# -*- coding: utf-8 -*-
import logging

from http import HTTPStatus
from flask.globals import request

from vantage6.server.resource import (
    with_user,
    ServicesResources
)
from vantage6.common import logger_name
from vantage6.server import db
from vantage6.server.model.base import DatabaseSessionManager
from vantage6.server.resource._schema import RuleSchema
from vantage6.server.resource.pagination import Pagination


module_name = logger_name(__name__)
log = logging.getLogger(module_name)
rule_schema = RuleSchema()


def setup(api, api_base, services):

    path = "/".join([api_base, module_name])
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Rules,
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
class Rules(ServicesResources):

    @with_user
    def get(self):
        """List Rules
        ---
        description: >-
            List of all available rules at the server. The user does not
            require any additional permissions to view these.\n\n

            Accessible for: `user`.\n\n

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
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        q = DatabaseSessionManager.get_session().query(db.Rule)

        # paginate results
        page = Pagination.from_query(q, request)

        # model serialization
        return self.response(page, rule_schema)


class Rule(ServicesResources):

    @with_user
    def get(self, id):
        """Returns a specific rule
        ---
        description: >-
            Inspect a specific rule. The user does not need any additional
            permissions to view these.

            Accessible as: `user`.

        parameters:
        - in: path
          name: id
          schema:
              type: integer
          minimum: 1
          description: rule_id
          required: true

        responses:
            200:
                description: Ok
            404:
                description: Rule not found
            401:
                description: Unauthorized

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        rule = db.Rule.get(id)
        if not rule:
            return {'msg': f'Rule id={id} not found!'}, HTTPStatus.NOT_FOUND

        return rule_schema.dump(rule, many=False).data, HTTPStatus.OK
