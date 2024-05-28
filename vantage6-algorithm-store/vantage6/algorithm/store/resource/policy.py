import logging

from http import HTTPStatus
from flask.globals import request
from flask import g
from flask_restful import Api

from vantage6.backend.common.resource.pagination import Pagination
from vantage6.common import logger_name
from vantage6.common.enum import StorePolicies as Policies
from vantage6.algorithm.store import db
from vantage6.algorithm.store.resource import (
    AlgorithmStoreResources,
    with_authentication,
)
from vantage6.algorithm.store.resource.schema.output_schema import PolicyOutputSchema
from vantage6.algorithm.store.model.common.enums import PublicPolicies

module_name = logger_name(__name__)
log = logging.getLogger(module_name)
policy_schema = PolicyOutputSchema()


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the rule resource.

    Parameters
    ----------
    api : Api
        Flask restful api instance
    api_base : str
        Base url of the api
    services : dict
        Dictionary with services required for the resource endpoints
    """
    path = "/".join([api_base, module_name])
    log.info('Setting up "%s" and subdirectories', path)

    api.add_resource(
        PrivatePoliciesAPI,
        path,
        endpoint="policies_without_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        PublicPoliciesAPI,
        f"{path}/public",
        endpoint="public_policies_without_id",
        methods=("GET",),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------


class PrivatePoliciesAPI(AlgorithmStoreResources):
    @with_authentication()
    def get(self):
        """List algorithm store policies
        ---
        description: >-
            List of all policies at the algorithm store. The user must be
            authenticated, but does not require any additional permissions to
            view the policies.

        parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name of the policy

        responses:
          200:
            description: Ok
          400:
            description: Improper values for policy name, pagination or sorting

        security:
            - bearerAuth: []

        tags: ["Policy"]
        """
        q = g.session.query(db.Policy)

        args = request.args

        # If there is a filter by policy name, filter by it, but raise error if it is
        # not in the PolicyInputSchema
        if "name" in args:
            q = q.filter(db.Policy.name == args["name"])
            if "name" not in [p.value for p in Policies]:
                return {
                    "msg": f"The policy '{args['name']}' does not exist!"
                }, HTTPStatus.BAD_REQUEST

        try:
            page = Pagination.from_query(q, request, db.Policy, paginate=False)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST
        # model serialization
        return self.response(page, policy_schema)


class PublicPoliciesAPI(AlgorithmStoreResources):
    def get(self):
        """List public algorithm store policies
        ---
        description: >-
            List of public policies at the algorithm store.

        parameters:
            - in: query
              name: name
              schema:
                type: string
              description: Filter by name of the policy

        responses:
          200:
            description: Ok
          400:
            description: Improper values for policy name, pagination or sorting

        tags: ["Policy"]
        """
        q = g.session.query(db.Policy).filter(
            db.Policy.key.in_([p.value for p in PublicPolicies])
        )

        args = request.args

        # If there is a filter by policy name, filter by it, but raise error if it is
        # not in the PolicyInputSchema
        if "name" in args:
            q = q.filter(db.Policy.name == args["name"])
            if "name" not in [p.value for p in PublicPolicies]:
                return {
                    "msg": f"The policy '{args['name']}' does not exist!"
                }, HTTPStatus.BAD_REQUEST

        try:
            page = Pagination.from_query(q, request, db.Policy, paginate=False)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST
        # model serialization
        return self.response(page, policy_schema)
