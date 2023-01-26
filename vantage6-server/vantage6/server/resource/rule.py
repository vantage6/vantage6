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
from vantage6.server.resource.common._schema import RuleSchema
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
            List of all available rules at the server. The user must be
            authenticated, but does not require any additional permissions to
            view the rules.\n

            Accesible to users.

        parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name of the rule
            - in: query
              name: operation
              schema:
                type: string
              description: Get rules for a specific type of operation
            - in: query
              name: scope
              schema:
                type: string
              description: Get rules for a specific scope
            - in: query
              name: role_id
              schema:
                type: integer
              description: Get rules for a specific role
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

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        q = DatabaseSessionManager.get_session().query(db.Rule)

        args = request.args

        # filter by any field of this endpoint
        for param in ['name', 'operation', 'scope']:
            if param in args:
                q = q.filter(getattr(db.Rule, param) == args[param])

        # find roles containing a specific rule
        if 'role_id' in args:
            q = q.join(db.role_rule_association).join(db.Role)\
                 .filter(db.Role.id == args['role_id'])

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
            Get a rule by it's id. The user must be authenticated, but does
            not require any additional permissions to view rules.\n

            Accesible to users.

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

        security:
            - bearerAuth: []

        tags: ["Rule"]
        """
        rule = db.Rule.get(id)
        if not rule:
            return {'msg': f'Rule id={id} not found!'}, HTTPStatus.NOT_FOUND

        return rule_schema.dump(rule, many=False).data, HTTPStatus.OK
