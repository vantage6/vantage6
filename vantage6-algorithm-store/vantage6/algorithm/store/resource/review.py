import logging
import datetime

from http import HTTPStatus
from threading import Thread

from flask import request, g, render_template, Flask, current_app
from flask_mail import Mail
from flask_restful import Api
from marshmallow import ValidationError
from sqlalchemy import select

from vantage6.common import logger_name
from vantage6.common.enum import StorePolicies
from vantage6.backend.common.resource.pagination import Pagination
from vantage6.backend.common.globals import (
    DEFAULT_EMAIL_FROM_ADDRESS,
    DEFAULT_SUPPORT_EMAIL_ADDRESS,
)
from vantage6.backend.common import get_server_url

from vantage6.algorithm.store.model.common.enums import ReviewStatus, AlgorithmStatus
from vantage6.algorithm.store.permission import PermissionManager, Operation as P
from vantage6.algorithm.store.resource import (
    with_permission,
    AlgorithmStoreResources,
)
from vantage6.algorithm.store import db
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.resource.schema.input_schema import (
    ReviewCreateInputSchema,
    ReviewUpdateInputSchema,
)
from vantage6.algorithm.store.resource.schema.output_schema import ReviewOutputSchema

module_name = logger_name(__name__)
log = logging.getLogger(module_name)


def setup(api: Api, api_base: str, services: dict) -> None:
    """
    Setup the review resource.

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
        methods=("GET", "DELETE"),
        resource_class_kwargs=services,
    )
    api.add_resource(
        ReviewApprove,
        path + "/<int:id>/approve",
        endpoint="review_approve",
        methods=("POST",),
        resource_class_kwargs=services,
    )
    api.add_resource(
        ReviewReject,
        path + "/<int:id>/reject",
        endpoint="review_reject",
        methods=("POST",),
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

    log.debug("Loading module reviews permission")
    add = permissions.appender(module_name)
    add(P.VIEW, description="View reviews")
    add(P.CREATE, description="Create new reviews")
    add(P.DELETE, description="Delete reviews")
    add(P.EDIT, description="Approve or reject reviews")


# ------------------------------------------------------------------------------
# Resources / API's
# ------------------------------------------------------------------------------
review_create_schema = ReviewCreateInputSchema()
review_update_schema = ReviewUpdateInputSchema()
review_output_schema = ReviewOutputSchema()


class ReviewBase(AlgorithmStoreResources):
    """Base class for /review endpoints"""

    @staticmethod
    def _is_reviewers_assignment_finished(reviews: list[db.Review]) -> bool:
        """
        Check if the reviewers assignment is finished for the given algorithm, according to the
        policies set. This is the case if:
        1. the minimum number of reviewers has been reached
        2. the minimum number of different organizations has been involved

        Parameters
        ----------
        reviews : list[db.Review]
            reviews of the algorithm

        Returns
        -------
        bool
            True if the reviewers assignment is finished, False otherwise
        """
        # get the number of unique organizations assigned to review the algorithm.
        # A unique organization is defined by the combination of organization id and server
        current_orgs = len(
            set(
                [(rev.reviewer.organization_id, rev.reviewer.server) for rev in reviews]
            )
        )

        return (
            current_orgs >= Policy.get_minimum_reviewing_orgs()
            and len(reviews) >= Policy.get_minimum_reviewers()
        )


class Reviews(ReviewBase):
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
        q = select(db.Review)

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
        data = request.get_json(silent=True)

        # validate request body
        try:
            data = review_create_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Invalid input",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        # check that the algorithm exists and has reviewable status
        algorithm: db.Algorithm = db.Algorithm.get(data["algorithm_id"])
        if not algorithm:
            return {"msg": "Algorithm not found"}, HTTPStatus.BAD_REQUEST
        if algorithm.is_review_finished():
            return {
                "msg": "Algorithm review is already finished!"
            }, HTTPStatus.BAD_REQUEST
        # check if a policy exist that allow the user to assign a review
        if not Policy.search_user_in_policy(
            g.user, StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value
        ):
            return {
                "msg": "You are not allowed to assign reviews due to the policy set "
                "by the administrator of this store."
            }, HTTPStatus.UNAUTHORIZED

        # check if the developer is the review assigner and if this is allowed
        if (
            algorithm.developer_id == g.user.id
            and not Policy.is_developer_allowed_assign_review()
        ):
            return {
                "msg": "This store does not allow developers to assign reviewers "
                "for their own algorithm"
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
                "msg": f"User id='{reviewer.id}' is not does not have the role of "
                "reviewer and is not allowed to review algorithms!"
            }, HTTPStatus.BAD_REQUEST
        # the developer of the algorithm may not review their own algorithm, unless
        # a different dev policy is set

        elif not Policy.search_user_in_policy(
            reviewer, StorePolicies.ALLOWED_REVIEWERS.value
        ):
            return {
                "msg": f"User id='{reviewer.id}' is not allowed to review algorithms, "
                "according to the policies set by the administrator of this store"
            }, HTTPStatus.BAD_REQUEST

        if reviewer == algorithm.developer and not self.config.get("dev", {}).get(
            "review_own_algorithm", False
        ):
            return {
                "msg": (
                    "You cannot assign the developer of the algorithm to review "
                    "their own algorithm!"
                )
            }, HTTPStatus.BAD_REQUEST
        if g.session.scalars(
            select(db.Review).filter(
                db.Review.algorithm_id == data["algorithm_id"],
                db.Review.reviewer_id == data["reviewer_id"],
            )
        ).first():
            return {
                "msg": "Reviewer has already reviewed this algorithm!"
            }, HTTPStatus.BAD_REQUEST

        # all checks OK, create the review
        review = db.Review(
            algorithm_id=data["algorithm_id"], reviewer_id=data["reviewer_id"]
        )
        review.save()

        # also update the algorithm status to 'under review' if policies are met:
        if self._is_reviewers_assignment_finished(algorithm.reviews):
            algorithm.status = AlgorithmStatus.UNDER_REVIEW
            algorithm.save()

        # send email to the reviewer to notify them of the new review
        Thread(
            target=self._send_email_to_reviewer,
            args=(
                current_app._get_current_object(),
                self.mail,
                review,
                g.user.username,
                self.config,
                request.headers.get("store_url"),
            ),
        ).start()

        return review_output_schema.dump(review), HTTPStatus.CREATED

    @staticmethod
    def _send_email_to_reviewer(
        app: Flask,
        mail: Mail,
        review: db.Review,
        review_assigner_username: str,
        config: dict,
        store_url: str | None,
    ) -> None:
        """
        Send an email to the reviewer to notify them of a new review assignment.

        Parameters
        ----------
        app : Flask
            Flask application instance
        mail : Mail
            Flask-Mail instance
        review : db.Review
            Review instance
        review_assigner_username : str
            Username of the user that assigned the review
        config : dict
            Configuration dictionary
        store_url : str | None
            URL of the store API
        """
        smtp_settings = config.get("smtp", {})
        if not smtp_settings:
            log.warning(
                "No SMTP settings found. No emails will be sent to alert the reviewer "
                "that they have been assigned a review."
            )
            return
        email_sender = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
        support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

        # get the reviewer's email address
        # TODO remove v5+ as all users should have an email address
        if not review.reviewer.email:
            log.warning(
                "No email address found for the reviewer %s (id %s). No email will be "
                "sent to alert the reviewer that they have been assigned a review.",
                review.reviewer.username,
                review.reviewer_id,
            )
            return
        log.info(
            "Sending email to reviewer %s (id %s) to notify them of a new review "
            "assignment.",
            review.reviewer.username,
            review.reviewer_id,
        )

        template_vars = {
            "reviewer_username": review.reviewer.username,
            "algorithm_name": review.algorithm.name,
            "dev_username": review.algorithm.developer.username,
            "assigner_username": review_assigner_username,
            "store_url": get_server_url(config, store_url),
            "server_url": review.reviewer.server.url,
            "support_email": support_email,
        }
        with app.app_context():
            mail.send_email(
                subject="New vantage6 algorithm to review",
                sender=email_sender,
                recipients=[review.reviewer.email],
                text_body=render_template("mail/new_review.txt", **template_vars),
                html_body=render_template("mail/new_review.html", **template_vars),
            )


class Review(ReviewBase):
    """Resource for the /review/<id> endpoint"""

    @with_permission(module_name, P.VIEW)
    def get(self, id):
        """Get a review by id

        ---
        description: Get a review by id

        parameters:
          - name: id
            in: path
            type: integer
            required: true
            description: ID of the review to get

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized
          404:
            description: Review not found

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        review = db.Review.get(id)
        if not review:
            return {"msg": "Review not found"}, HTTPStatus.NOT_FOUND

        return review_output_schema.dump(review), HTTPStatus.OK

    @with_permission(module_name, P.DELETE)
    def delete(self, id):
        """Remove a review

        ---
        description: Remove a review

        parameters:
          - name: id
            in: path
            type: integer
            required: true
            description: ID of the review to remove

        responses:
          200:
            description: Ok
          400:
            description: Reviews of approved algorithms may not be deleted
          401:
            description: Unauthorized
          404:
            description: Review not found

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        review: db.Review = db.Review.get(id)
        if not review:
            return {"msg": "Review not found"}, HTTPStatus.NOT_FOUND

        # update the algorithm status if the algorithm is still under review
        # 1. set to approved if there is at least one other review and all other
        #    reviews are approved
        # 2. set to awaiting reviewer assignment if there are no other reviews
        algorithm: db.Algorithm = review.algorithm
        if not algorithm.is_review_finished():
            # if number of reviews after deletion is less than the minium,
            # new reviewers should be assigned
            other_reviews = [r for r in algorithm.reviews if not r.id == review.id]
            if not other_reviews or not self._is_reviewers_assignment_finished(
                other_reviews
            ):
                algorithm.status = AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
            elif all([r.status == ReviewStatus.APPROVED for r in other_reviews]):
                # if this was the last remaining review that needed to be approved, but
                # it is now deleted, the algorithm should be approved
                algorithm.status = AlgorithmStatus.APPROVED
            algorithm.save()
        elif algorithm.status == AlgorithmStatus.APPROVED:
            # for algorithms that are currently approved, the reviews may not be
            # deleted.
            return {
                "msg": "Reviews of approved algorithms may not be deleted!"
            }, HTTPStatus.FORBIDDEN

        review.delete()
        log.info("Review with id=%s deleted", id)
        return {"msg": f"Review id={id} has been deleted"}, HTTPStatus.OK


class ReviewUpdateResources(AlgorithmStoreResources):
    @staticmethod
    def send_email_review_update(
        app: Flask,
        mail: Mail,
        algorithm: db.Algorithm,
        is_approved: bool,
        config: dict,
        store_url: str | None,
    ) -> None:
        """
        Send an email to the algorithm developer to alert them that their algorithm has
        been rejected or approved.

        Parameters
        ----------
        app : Flask
            Flask application instance
        mail : Mail
            Flask-Mail instance
        algorithm : db.Algorithm
            Algorithm instance
        is_approved : bool
            Whether the algorithm has been approved (True) or rejected (False)
        config : dict
            Configuration dictionary
        store_url : str | None
            URL of the store API
        """
        smtp_settings = config.get("smtp", {})
        if not smtp_settings:
            log.warning(
                "No SMTP settings found. No emails will be sent to alert the reviewer "
                "that they have been assigned a review."
            )
            return
        email_sender = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
        support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

        # get the developer's email address
        # TODO remove v5+ as all users should have an email address
        status_text = "approved" if is_approved else "rejected"
        if not algorithm.developer.email:
            log.warning(
                "No email address found for the developer %s (id %s). No email will be "
                "sent to alert the developer that their algorithm has been %s.",
                algorithm.developer.username,
                algorithm.developer_id,
                status_text,
            )
            return
        log.info(
            "Sending email to developer %s (id %s) to notify them that their algorithm "
            "has been %s.",
            algorithm.developer.username,
            algorithm.developer_id,
            status_text,
        )

        final_paragraph = (
            (
                "Congratulations! Your algorithm is now available to be used by "
                "everyone that has access to this algorithm store."
            )
            if is_approved
            else (
                "Unfortunately, your algorithm has been rejected. Please check the "
                "review comments for more information, and take them into account "
                "before resubmitting your algorithm."
            )
        )

        template_vars = {
            "developer_username": algorithm.developer.username,
            "algorithm_name": algorithm.name,
            "status_text": status_text,
            "store_url": get_server_url(config, store_url),
            "final_paragraph": final_paragraph,
            "support_email": support_email,
        }
        with app.app_context():
            mail.send_email(
                subject=(
                    f"Your Vantage6 algorithm {algorithm.name} has been {status_text}"
                ),
                sender=email_sender,
                recipients=[algorithm.developer.email],
                text_body=render_template(
                    "mail/algorithm_review_finalized.txt", **template_vars
                ),
                html_body=render_template(
                    "mail/algorithm_review_finalized.html", **template_vars
                ),
            )


class ReviewApprove(ReviewUpdateResources):
    """Resource for the /review/<id>/approve endpoint"""

    @with_permission("review", P.EDIT)
    def post(self, id):
        """Approve an algorithm in the current review

        ---
        description: Approve a algorithm in the current review

        parameters:
          - name: id
            in: path
            type: integer
            required: true
            description: ID of the review to approve
          - comment: str
            in: query
            required: false
            description: Comment to add to the review

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized, or not assigned to this review
          403:
            description: Reviewer is not assigned to this review
          404:
            description: Review not found

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        data = request.get_json(silent=True)

        # validate input
        try:
            data = review_update_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Invalid input",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        review = db.Review.get(id)
        if not review:
            return {"msg": "Review not found"}, HTTPStatus.NOT_FOUND

        # check that the reviewer is assigned to this review
        if review.reviewer_id != g.user.id:
            return {"msg": "You are not assigned to this review!"}, HTTPStatus.FORBIDDEN

        # check if review can still be approved
        if review.status != ReviewStatus.UNDER_REVIEW:
            return {
                "msg": f"This review has status {review.status} so it can no longer be "
                "approved!"
            }, HTTPStatus.BAD_REQUEST

        # update the review status to 'approved'
        review.status = ReviewStatus.APPROVED
        if comment := data.get("comment"):
            review.comment = comment
        review.save()

        # also update the algorithm status to 'approved' if this was the last review
        # that needed to be approved
        algorithm: db.Algorithm = review.algorithm
        if (
            algorithm.status == AlgorithmStatus.UNDER_REVIEW
            and algorithm.are_all_reviews_approved()
        ):
            algorithm.approve()

            # notify the developer by email that their algorithm has been approved
            Thread(
                target=self.send_email_review_update,
                args=(
                    current_app._get_current_object(),
                    self.mail,
                    algorithm,
                    True,
                    self.config,
                    request.headers.get("store_url"),
                ),
            ).start()

        log.info("Review with id=%s has been approved", id)
        return {"msg": f"Review id={id} has been approved"}, HTTPStatus.OK


class ReviewReject(ReviewUpdateResources):
    """Resource for the /review/<id>/reject endpoint"""

    @with_permission("review", P.EDIT)
    def post(self, id):
        """Reject an algorithm in the current review

        ---
        description: Reject a algorithm in the current review

        parameters:
          - name: id
            in: path
            type: integer
            required: true
            description: ID of the review to reject
          - comment: str
            in: query
            required: false
            description: Comment to add to the review

        responses:
          200:
            description: Ok
          401:
            description: Unauthorized, or not assigned to this review
          403:
            description: Reviewer is not assigned to this review
          404:
            description: Review not found

        security:
          - bearerAuth: []

        tags: ["Review"]
        """
        data = request.get_json(silent=True)

        # validate input
        try:
            data = review_update_schema.load(data)
        except ValidationError as e:
            return {
                "msg": "Invalid input",
                "errors": e.messages,
            }, HTTPStatus.BAD_REQUEST

        review: db.Review = db.Review.get(id)
        if not review:
            return {"msg": "Review not found"}, HTTPStatus.NOT_FOUND

        # check that the reviewer is assigned to this review
        if review.reviewer_id != g.user.id:
            return {"msg": "You are not assigned to this review!"}, HTTPStatus.FORBIDDEN

        # check if review can still be rejected
        if review.status != ReviewStatus.UNDER_REVIEW:
            return {
                "msg": f"This review has status {review.status} so it can no longer be "
                "approved!"
            }, HTTPStatus.BAD_REQUEST

        # update the review status to 'rejected'
        review.status = ReviewStatus.REJECTED
        if comment := data.get("comment"):
            review.comment = comment
        review.save()

        # also update the algorithm status to 'rejected'
        algorithm: db.Algorithm = review.algorithm
        algorithm.status = AlgorithmStatus.REJECTED
        algorithm.invalidated_at = datetime.datetime.now(datetime.timezone.utc)
        algorithm.save()

        # the other reviews of this algorithm are dropped as they are no longer required
        for other_review in algorithm.reviews:
            if other_review.id == review.id:
                continue
            other_review.status = ReviewStatus.DROPPED
            other_review.save()

            # notify the reviewer by email that this review is no longer necessary
            Thread(
                target=self._send_email_review_dropped,
                args=(
                    current_app._get_current_object(),
                    self.mail,
                    other_review,
                    self.config,
                    request.headers.get("store_url"),
                ),
            ).start()

        # Notify the developer that their algorithm has been rejected
        Thread(
            target=self.send_email_review_update,
            args=(
                current_app._get_current_object(),
                self.mail,
                algorithm,
                False,
                self.config,
                request.headers.get("store_url"),
            ),
        ).start()

        # note that we do not invalidate the previously approved versions here, as the
        # algorithm is rejected and not replaced by a new version

        log.info("Review with id=%s has been rejected", id)
        return {"msg": f"Review id={id} has been rejected"}, HTTPStatus.OK

    @staticmethod
    def _send_email_review_dropped(
        app: Flask,
        mail: Mail,
        review: db.Review,
        config: dict,
        store_url: str | None,
    ) -> None:
        """
        Send an email to the reviewer to notify them that their review is no longer
        necessary, because the algorithm has been rejected.

        Parameters
        ----------
        app : Flask
            Flask application instance
        mail : Mail
            Flask-Mail instance
        review : db.Review
            Review instance
        config : dict
            Configuration dictionary
        store_url : str | None
            URL of the store API
        """
        smtp_settings = config.get("smtp", {})
        if not smtp_settings:
            log.warning(
                "No SMTP settings found. No emails will be sent to alert the reviewer "
                "that their review is no longer required."
            )
            return
        email_sender = smtp_settings.get("email_from", DEFAULT_EMAIL_FROM_ADDRESS)
        support_email = config.get("support_email", DEFAULT_SUPPORT_EMAIL_ADDRESS)

        # get the reviewer's email address
        # TODO remove v5+ as all users should have an email address
        if not review.reviewer.email:
            log.warning(
                "No email address found for the reviewer %s (id %s). No email will be "
                "sent to alert the reviewer that their review is no longer required.",
                review.reviewer.username,
                review.reviewer_id,
            )
            return
        log.info(
            "Sending email to reviewer %s (id %s) to notify them that their review is "
            "no longer required.",
            review.reviewer.username,
            review.reviewer_id,
        )

        template_vars = {
            "reviewer_username": review.reviewer.username,
            "algorithm_name": review.algorithm.name,
            "store_url": get_server_url(config, store_url),
            "support_email": support_email,
        }
        with app.app_context():
            mail.send_email(
                subject="Vantage6 algorithm review no longer required",
                sender=email_sender,
                recipients=[review.reviewer.email],
                text_body=render_template(
                    "mail/review_no_longer_required.txt", **template_vars
                ),
                html_body=render_template(
                    "mail/review_no_longer_required.html", **template_vars
                ),
            )
