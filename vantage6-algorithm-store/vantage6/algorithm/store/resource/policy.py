import logging
from http import HTTPStatus

from flask import g
from flask.globals import request
from flask_restful import Api
from sqlalchemy import select

from vantage6.common import logger_name
from vantage6.common.enum import StorePolicies

from vantage6.algorithm.store import db
from vantage6.algorithm.store.model.common.enums import (
    BooleanPolicies,
    DefaultStorePolicies,
    ListPolicies,
    PublicPolicies,
)
from vantage6.algorithm.store.resource import (
    AlgorithmStoreResources,
    with_authentication,
)

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


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


class PoliciesBase(AlgorithmStoreResources):
    """Base class for /policy endpoints"""

    def policies_to_dict(
        self,
        policies: list[db.Policy],
        include_defaults: bool = False,
        include_private: bool = False,
    ) -> dict:
        """
        Convert policies to dictionary that will be returned in the response

        Parameters
        ----------
        policies : list[Policy]
            List of policies to convert to dictionary
        include_defaults : bool
            Include default values for policies that are not in the response. By default
            this is set to False.
        include_private : bool
            This value only matters if include_defaults is set to True: then it
            determines whether non-public policies are included. Default is False.

        Returns
        -------
        dict
            Dictionary with policies
        """
        # reshape the policies to a more readable format
        # e.g. from
        #   {'value': 'public', 'key': 'algorithm_view'},
        # to
        #   {'algorithm_view': 'public'}
        response_dict = {}
        for policy in policies:
            policy_name = policy.key
            if policy_name in response_dict:
                # if policy exists, then append to list of values
                if isinstance(response_dict[policy_name], list):
                    response_dict[policy_name].append(policy.value)
                else:
                    response_dict[policy_name] = [
                        response_dict[policy_name],
                        policy.value,
                    ]
            else:
                response_dict[policy_name] = policy.value

        # convert policies where necessary
        for boolean_policy in BooleanPolicies.list():
            if boolean_policy in response_dict:
                response_dict[boolean_policy] = (
                    response_dict[boolean_policy] == "1"
                    or response_dict[boolean_policy].lower() == "true"
                    or response_dict[boolean_policy] is True
                )
        for list_policy in ListPolicies.list():
            if list_policy in response_dict and isinstance(
                response_dict[list_policy], str
            ):
                response_dict[list_policy] = [response_dict[list_policy]]

        # add default values for policies that are not in the response
        if include_defaults:
            all_policies = StorePolicies if include_private else PublicPolicies
            for policy in all_policies.list():
                if policy not in response_dict:
                    response_dict[policy] = DefaultStorePolicies[policy.upper()].value

        return response_dict


class PrivatePoliciesAPI(PoliciesBase):
    """Resource for /api/policy"""

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
        q = select(db.Policy)

        args = request.args

        # If there is a filter by policy name, filter by it, but raise error if it is
        # not in the PolicyInputSchema
        if "name" in args:
            q = q.filter(db.Policy.name == args["name"])
            if "name" not in StorePolicies.list():
                return {
                    "msg": f"The policy '{args['name']}' does not exist!"
                }, HTTPStatus.BAD_REQUEST

        policies_dict = self.policies_to_dict(
            g.session.scalars(q).all(), include_defaults=True, include_private=True
        )

        return policies_dict, HTTPStatus.OK


class PublicPoliciesAPI(PoliciesBase):
    """Resource for /api/policy/public"""

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
          401:
            description: Policy is not public

        tags: ["Policy"]
        """
        q = select(db.Policy).filter(db.Policy.key.in_(PublicPolicies.list()))

        args = request.args

        # If there is a filter by policy name, filter by it, but raise error if it is
        # not in the PolicyInputSchema
        if "name" in args:
            q = q.filter(db.Policy.name == args["name"])
            if "name" not in StorePolicies.list():
                return {
                    "msg": f"The policy '{args['name']}' does not exist!"
                }, HTTPStatus.BAD_REQUEST
            elif "name" not in PublicPolicies.list():
                return {
                    "msg": f"The policy '{args['name']}' is not public! You need to "
                    "be authenticated to view it."
                }, HTTPStatus.UNAUTHORIZED

        policies_dict = self.policies_to_dict(
            g.session.scalars(q).all(), include_defaults=True, include_private=False
        )

        return policies_dict, HTTPStatus.OK
