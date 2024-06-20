import logging

from http import HTTPStatus
from flask import request, g
from flask_restful import Api


from vantage6.common import logger_name
from vantage6.backend.common.resource.pagination import Pagination

from vantage6.algorithm.store.model.common.enums import ReviewStatus
from vantage6.algorithm.store.permission import PermissionManager, Operation as P
from vantage6.algorithm.store.resource import (
    with_permission,
    AlgorithmStoreResources,
)
from vantage6.algorithm.store import db
from vantage6.algorithm.store.resource.schema.input_schema import (
    ReviewCreateInputSchema,
    ReviewUpdateInputSchema,
)
from vantage6.algorithm.store.resource.schema.output_schema import ReviewOutputSchema


module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the user resource.

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
    log.info(f'Setting up "{path}" and subdirectories')

    api.add_resource(
        Reviews,
        path,
        endpoint="review_without_id",
        methods=("GET", "POST"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        Review,
        path + "/<int:id>",
        endpoint="review_with_id",
        methods=("GET", "PATCH", "DELETE"),
        resource_class_kwargs=services,
    )


# ------------------------------------------------------------------------------
# Permissions
# ------------------------------------------------------------------------------


def permissions(permissions: PermissionManager) -> None:
    """
    Define the permissions for this resource.

    Parameters
    ----------
    permissions : PermissionManager
        Permission manager instance to which permissions are added
    """

    log.debug("Loading module users permission")
    add = permissions.appender(module_name)
    add(P.VIEW, description="View any user")
    add(P.CREATE, description="Create a new user")
    add(P.EDIT, description="Edit any user")
    add(P.DELETE, description="Delete any user")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
review_create_schema = ReviewCreateInputSchema()
review_update_schema = ReviewUpdateInputSchema()
review_output_schema = ReviewOutputSchema()


class Reviews(AlgorithmStoreResources):
    """Resource for the /review endpoint"""

    @with_permission(module_name, P.VIEW)
    def get(self):
        """List reviews
        ---
        description: List algorithm reviews

        parameters:
          - name: algorithm_id
            in: query
            type: integer
            required: false
            description: Filter reviews by algorithm id
          - name: reviewer_id
            in: query
            type: integer
            required: false
            description: Filter reviews by reviewer id
          - name: under_review
            in: query
            type: boolean
            required: false
            description: Filter reviews that are currently under review. Cannot be
              combined with 'reviewed', 'approved' or 'rejected'
          - name: reviewed
            in: query
            type: boolean
            required: false
            description: Filter reviews that have been reviewed. Cannot be combined
              with 'under_review'
          - name: approved
            in: query
            type: boolean
            required: false
            description: Filter reviews that have been approved. Cannot be combined
              with 'rejected' or 'under_review'
          - name: rejected
            in: query
            type: boolean
            required: false
            description: Filter reviews that have been rejected. Cannot be combined
              with 'approved' or 'under_review'
          - in: query
            name: page
            schema:
              type: integer
            description: Page number for pagination (default=1)
          - in: query
            name: per_page
            schema:
              type: integer
            description: Number of items per page (default=10)
          - in: query
            name: sort
            schema:
              type: string
            description: >-
              Sort by one or more fields, separated by a comma. Use a minus
              sign (-) in front of the field to sort in descending order.

        responses:
          200:
            description: Ok
          400:
            description: Invalid values provided for request parameters
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        q = g.session.query(db.Review)

        # filter by simple filters
        if algorithm_id := request.args.get("algorithm_id"):
            q = q.filter(db.Review.algorithm_id == algorithm_id)
        if reviewer_id := request.args.get("reviewer_id"):
            q = q.filter(db.Review.reviewer_id == reviewer_id)

        # check that no conflicting status filters are provided. Note that the status
        # 'reviewed' may be combined with 'approved' or 'rejected'
        under_review = bool(request.args.get("under_review", False))
        reviewed = bool(request.args.get("reviewed", False))
        approved = bool(request.args.get("approved", False))
        rejected = bool(request.args.get("rejected", False))
        status_filters = [under_review, approved, rejected]
        if sum(status_filters) > 1:
            return {
                "msg": "You have provided multiple review statuses that are "
                "conflicting!"
            }, HTTPStatus.BAD_REQUEST
        if reviewed and under_review:
            return {
                "msg": "You have provided multiple review statuses that are "
                "conflicting!"
            }, HTTPStatus.BAD_REQUEST

        # filter by review status
        if under_review:
            q = q.filter(db.Review.status == ReviewStatus.UNDER_REVIEW)
        if reviewed:
            q = q.filter(
                db.Review.status.in_([ReviewStatus.APPROVED, ReviewStatus.REJECTED])
            )
        if approved:
            q = q.filter(db.Review.status == ReviewStatus.APPROVED)
        if rejected:
            q = q.filter(db.Review.status == ReviewStatus.REJECTED)

        # paginate results
        try:
            page = Pagination.from_query(q, request, db.User)
        except (ValueError, AttributeError) as e:
            return {"msg": str(e)}, HTTPStatus.BAD_REQUEST

        # model serialization
        return self.response(page, review_output_schema)

    @with_permission(module_name, P.CREATE)
    def post(self):
        """Create a new review

        ---
        description: Create a new review

        requestBody:
          content:
            application/json:
              schema:
                properties:
                  algorithm_id:
                    type: integer
                  reviewer_id:
                    type: integer

        responses:
          201:
            description: Created
          400:
            description: Invalid values provided for request parameters
          401:
            description: Unauthorized

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        data = request.get_json()

        # validate request body
        errors = review_create_schema.validate(data)
        if errors:
            return {"msg": "Invalid input", "errors": errors}, HTTPStatus.BAD_REQUEST

        # check that the algorithm exists and has reviewable status
        algorithm: db.Algorithm = db.Algorithm.get(data["algorithm_id"])
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.BAD_REQUEST
        if algorithm.is_review_finished():
            return {
                "msg": "Algorithm review is already finished!"
            }, HTTPStatus.BAD_REQUEST

        # check that
        # 1. the assigned reviewer exists
        # 2. that they are allowed to review
        # 3. that they are not the developer of the algorithm
        # 4. that they have not already reviewed the algorithm
        reviewer: db.User = db.User.get(data["reviewer_id"])
        if not reviewer:
            return {"msg": "Reviewer not found"}, HTTPStatus.BAD_REQUEST
        if not reviewer.is_reviewer():
            return {
                "msg": f"User id='{reviewer.id}' is not allowed to review algorithms!"
            }, HTTPStatus.BAD_REQUEST
        if reviewer == algorithm.developer:
            return {
                "msg": (
                    "You cannot assign the developer of the algorithm to review "
                    "their own algorithm!"
                )
            }, HTTPStatus.BAD_REQUEST
        if (
            g.session.query(db.Review)
            .filter(
                db.Review.algorithm_id == data["algorithm_id"],
                db.Review.reviewer_id == data["reviewer_id"],
            )
            .first()
        ):
            return {
                "msg": "Reviewer has already reviewed this algorithm!"
            }, HTTPStatus.BAD_REQUEST

        # all checks OK, create the review
        review = db.Review(
            algorithm_id=data["algorithm_id"], reviewer_id=data["reviewer_id"]
        )
        review.save()

        # also update the algorithm status to 'under review'
        algorithm.status = ReviewStatus.UNDER_REVIEW
        algorithm.save()

        return review_output_schema.dump(review), HTTPStatus.CREATED


class Review(AlgorithmStoreResources):
    """Resource for the /review/<id> endpoint"""

    @with_permission(module_name, P.VIEW)
    def get(self, id):
        pass

    @with_permission(module_name, P.EDIT)
    def patch(self, id):
        pass

    @with_permission(module_name, P.DELETE)
    def delete(self, id):
        pass
