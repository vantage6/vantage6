import logging
from functools import wraps
from http import HTTPStatus

from flask import g, request
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from flask_mail import Mail
from flask_restful import Api

from vantage6.common import logger_name
from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies

from vantage6.backend.common.services_resources import BaseServicesResources

from vantage6.algorithm.store import PermissionManager
from vantage6.algorithm.store.model.common.enums import DefaultStorePolicies
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.rule import Operation
from vantage6.algorithm.store.model.user import User

log = logging.getLogger(logger_name(__name__))


class AlgorithmStoreResources(BaseServicesResources):
    """
    Flask resource class for the algorithm store.

    Attributes
    ----------
    api : Api
        Api instance
    config: dict
        Configuration dictionary
    permissions : PermissionManager
        Permission manager instance
    mail : Mail
        Flask Mail instance
    """

    def __init__(
        self, api: Api, config: dict, permissions: PermissionManager, mail: Mail
    ):
        super().__init__(api, config, permissions, mail)


def _authenticate(*args, **kwargs) -> tuple[User | dict, HTTPStatus]:
    """
    Authenticate with a vantage6 algorithm store.

    Returns
    -------
    tuple[User | dict, HTTPStatus]
        Tuple containing a user object or a dict with an error message, and a status
        code.
    """
    verify_jwt_in_request()
    identity = get_jwt_identity()

    if not (user := User.get_by_keycloak_id(keycloak_id=identity)):
        return {"msg": "User not registered at store"}, HTTPStatus.UNAUTHORIZED

    g.user = user

    return user, HTTPStatus.OK


def _authorize_user(
    user: User, resource: str, operation: Operation
) -> tuple[dict, HTTPStatus] | None:
    """
    Authorize the user to perform an operation on a resource.

    Parameters
    ----------
    auth_response : requests.Response
        Response object from the authentication request.
    resource : str
        Name of the resource to check the view permission of.
    operation: Operation
        Operation to check the permission for.

    Returns
    -------
    tuple[dict, HTTPStatus] | None
        Tuple containing an error message and status code if the user is not
        authorized, None otherwise.
    """
    g.user = user
    if not user.can(resource, operation):
        msg = (
            f"You are not allowed to perform the operation '{operation}' on "
            f"resource '{resource}'"
        )

        log.warning(msg)
        return {"msg": msg}, HTTPStatus.UNAUTHORIZED

    # User is authorized
    return None, None


def with_authentication() -> callable:
    """
    Decorator to verify that the user is authenticated from the linked Keycloak service.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user_or_error, status = _authenticate(request)

            if status != HTTPStatus.OK:
                return user_or_error, status

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator


def with_permission(resource: str, operation: Operation) -> callable:
    """
    Decorator to verify that the user has as a permission on a resource.
    Parameters
    ----------
    resource : str
        Name of the resource to check the view permission of.
    operation: Operation
        Operation to check the permission for.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user_or_error, status = _authenticate(request)

            if status != HTTPStatus.OK:
                return user_or_error, status

            response, status = _authorize_user(user_or_error, resource, operation)
            if response is not None:
                return response, status

            # all good, proceed with function
            return fn(*args, **kwargs)

        return decorator

    return protection_decorator


def with_permission_to_view_algorithms() -> callable:
    """
    Decorator to verify that the user has as a permission on a resource.

    Returns
    -------
    callable
        Decorated function that can be used to access endpoints that require
        authentication.
    """

    def protection_decorator(fn):
        @wraps(fn)
        def decorator(self, *args, **kwargs):
            policies = Policy.get_as_dict()
            # check if everyone has permission to view algorithms
            algorithm_view_policy = policies.get(
                StorePolicies.ALGORITHM_VIEW.value,
                DefaultStorePolicies.ALGORITHM_VIEW.value,
            )

            # check if user is trying to view algorithms that are not approved by review
            # or have been invalidated - these algorithms always require authentication
            # even when algorithms are open to all
            request_args = request.args or {}
            request_approved = not (
                request_args.get("awaiting_reviewer_assignment")
                or request_args.get("under_review")
                or request_args.get("in_review_process")
                or request_args.get("invalidated")
            )

            # if the algorithm is public and approved, allow access
            if (
                algorithm_view_policy == AlgorithmViewPolicies.PUBLIC
                and request_approved
            ):
                return fn(self, *args, **kwargs)

            # not everyone has permission: authenticate with server
            user_or_error, status = _authenticate(request)
            if status != HTTPStatus.OK:
                return user_or_error, status

            # if user is authenticated an anyone with token can view algorithms, allow
            if (
                algorithm_view_policy == AlgorithmViewPolicies.AUTHENTICATED
                and request_approved
            ):
                return fn(self, *args, **kwargs)

            # not all authenticated users have permission: authorize user
            response, status = _authorize_user(
                user_or_error, "algorithm", Operation.VIEW
            )
            if response is not None:
                return response, status

            # all good, proceed with function
            return fn(self, *args, **kwargs)

        return decorator

    return protection_decorator
