from http import HTTPStatus
import unittest
from unittest.mock import patch

from tests_store.base.unittest_base import MockResponse, TestResources
from vantage6.algorithm.store.model import Policy
from vantage6.common.enum import StorePolicies
from vantage6.common.globals import Ports
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, ReviewStatus
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.rule import Rule, Operation

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"
REVIEWER_USERNAME_1 = "reviewer_user_1"
REVIEWER_USERNAME_2 = "reviewer_user_2"


class TestReviewResources(TestResources):
    """Test the review resources"""

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_view_multi(self, validate_token_mock):
        """Test GET /api/review"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # create a few reviews
        r1 = Review(status=ReviewStatus.UNDER_REVIEW)
        r2 = Review(status=ReviewStatus.APPROVED)
        r3 = Review(status=ReviewStatus.REJECTED)
        r4 = Review(status=ReviewStatus.DROPPED)
        # pylint: disable=expression-not-assigned
        [r.save() for r in [r1, r2, r3, r4]]

        # register server
        server = self.register_server()

        # check that getting reviews without authentication fails
        response = self.app.get("/api/review", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to view reviews
        self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.VIEW)],
        )

        # check that getting reviews with authentication succeeds
        response = self.app.get("/api/review", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Review.get()))

        # check that filtering works
        response = self.app.get("/api/review?under_review=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)
        response = self.app.get("/api/review?reviewed=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 2)
        response = self.app.get("/api/review?approved=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)
        response = self.app.get("/api/review?rejected=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)

        # check that conflicting statuses cannot be combined
        response = self.app.get(
            "/api/review?under_review=1&reviewed=1", headers=HEADERS
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        response = self.app.get("/api/review?approved=1&rejected=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that double filtering works if not conflicting
        response = self.app.get("/api/review?reviewed=1&approved=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)
        response = self.app.get("/api/review?reviewed=1&rejected=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)

        # cleanup
        [r.delete() for r in Review.get()]

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_view_single(self, validate_token_mock):
        """Test GET /api/review/<int:id>"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # create a review
        review = Review(status=ReviewStatus.UNDER_REVIEW)
        review.save()

        # register server
        server = self.register_server()

        # check that getting reviews without authentication fails
        response = self.app.get("/api/review", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to view reviews
        self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.VIEW)],
        )

        # check that getting reviews with authentication succeeds
        response = self.app.get(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json["id"], review.id)

        # check that getting a non-existing review fails
        response = self.app.get("/api/review/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # cleanup
        review.delete()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_create(self, validate_token_mock):
        """Test POST /api/review"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # register server
        server = self.register_server()

        # check that creating a review without authentication fails
        response = self.app.post("/api/review", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to create reviews
        developer = self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.CREATE)],
        )
        # register users allowed to do reviews
        reviewer = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        another_reviewer = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_2,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        # register another user not allowed to do reviews
        user_wo_permission = self.register_user(server.id, username="not_reviewer")

        # create algorithm
        algorithm = Algorithm(
            status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT, developer=developer
        )
        algorithm.save()

        json_body = {
            "algorithm_id": algorithm.id,
            "reviewer_id": reviewer.id,
        }

        # check that status cannot be set when creating review
        response = self.app.post(
            "/api/review",
            headers=HEADERS,
            json={
                **json_body,
                "status": ReviewStatus.APPROVED,
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that assigning a review to the algorithm developer fails
        json_body["reviewer_id"] = developer.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that assigning a review to a user without permission fails
        json_body["reviewer_id"] = user_wo_permission.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # create a review to a proper user
        # check that the developer cannot assign a review
        json_body["reviewer_id"] = reviewer.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # allow self review and check that the developer can assign now a review
        Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM, value=True).save()
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # check that you cannot create the same review twice, as user is already
        # assigned to review the algorithm
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that review cannot be assigned if algorithm is not awaiting review
        algorithm.status = AlgorithmStatus.APPROVED
        algorithm.save()
        json_body["reviewer_id"] = another_reviewer.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that you can assign a second reviewer
        algorithm.status = AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
        algorithm.save()
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # check that review cannot be created for non-existing algorithm
        json_body["algorithm_id"] = 9999
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_delete(self, validate_token_mock):
        """Test DELETE /api/review/<int:id>"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # create algorithm and review
        algorithm = Algorithm(
            status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT,
        )
        algorithm.save()
        review = Review(status=ReviewStatus.UNDER_REVIEW, algorithm=algorithm)
        review.save()

        # register server
        server = self.register_server()

        # check that deleting a review without authentication fails
        response = self.app.delete(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to delete reviews
        self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.DELETE)],
        )

        # check that deleting a review with authentication succeeds
        response = self.app.delete(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that deleting a non-existing review fails
        response = self.app.delete("/api/review/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        # register user allowed to approve reviews
        reviewer = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        # re-create review
        review = Review(status=ReviewStatus.UNDER_REVIEW, algorithm=algorithm)
        review.save()

        # check that deleting reviews for currently approved algorithms is not allowed
        algorithm.status = AlgorithmStatus.APPROVED
        algorithm.save()
        response = self.app.delete(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that if algorithm status is updated to awaiting review if only review
        # is deleted
        algorithm.status = AlgorithmStatus.UNDER_REVIEW
        algorithm.save()
        response = self.app.delete(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        algorithm = Algorithm.get(algorithm.id)
        self.assertEqual(algorithm.status, AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT)
        review = None  # update deleted sqlalchemy object to prevent warnings

        # set policy to require one review and one organization
        Policy(key=StorePolicies.MIN_REVIEWERS, value=1).save()
        Policy(key=StorePolicies.MIN_REVIEWING_ORGANIZATIONS, value=1).save()

        # check that if there are two reviews, one of which is approved and the other is
        # deleted, the algorithm status is updated to approved
        approved_review = Review(
            status=ReviewStatus.APPROVED, algorithm=algorithm, reviewer=reviewer
        )
        approved_review.save()
        # re-create review again
        review = Review(
            status=ReviewStatus.UNDER_REVIEW, algorithm=algorithm, reviewer=reviewer
        )
        review.save()
        response = self.app.delete(f"/api/review/{review.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        algorithm = Algorithm.get(algorithm.id)
        self.assertEqual(algorithm.status, AlgorithmStatus.APPROVED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_approve(self, validate_token_mock):
        """Test POST /api/review/<int:id>/approve"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # create algorithm
        current_algorithm = Algorithm(status=AlgorithmStatus.APPROVED, image="image")
        current_algorithm.save()
        new_algorithm = Algorithm(status=AlgorithmStatus.UNDER_REVIEW, image="image")
        new_algorithm.save()

        # register server
        server = self.register_server()

        # check that approving a review without authentication fails
        response = self.app.post("/api/review/1/approve", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to approve reviews
        reviewer = self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        another_reviewer = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )

        # create reviews
        review = Review(
            status=ReviewStatus.UNDER_REVIEW, algorithm=new_algorithm, reviewer=reviewer
        )
        review.save()
        another_review = Review(
            status=ReviewStatus.UNDER_REVIEW,
            algorithm=new_algorithm,
            reviewer=another_reviewer,
        )
        another_review.save()

        # check that approving non-existing review fails
        response = self.app.post("/api/review/9999/approve", headers=HEADERS, json={})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # check that approving review fails if it was already approved or rejected
        review.status = ReviewStatus.APPROVED
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/approve", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        review.status = ReviewStatus.REJECTED
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/approve", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that user cannot approve a review that is not assigned to them
        response = self.app.post(
            f"/api/review/{another_review.id}/approve", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # approve the second review so that the first one can be approved with the
        # side-effects of the algorithm status being updated
        another_review.status = ReviewStatus.APPROVED
        another_review.save()

        # check that approving a review with authentication succeeds, and that the
        # algorithm status is updated to approved
        body_ = {"comment": "Awesome algorithm!"}
        review.status = ReviewStatus.UNDER_REVIEW
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/approve", headers=HEADERS, json=body_
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        review = Review.get(review.id)
        self.assertEqual(review.comment, body_["comment"])
        self.assertEqual(review.status, ReviewStatus.APPROVED.value)
        algorithm = Algorithm.get(new_algorithm.id)
        self.assertEqual(algorithm.status, AlgorithmStatus.APPROVED)
        # check also that old algorithm is replaced by the new one
        current_algorithm = Algorithm.get(current_algorithm.id)
        self.assertEqual(current_algorithm.status, AlgorithmStatus.REPLACED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_review_reject(self, validate_token_mock):
        """Test POST /api/review/<int:id>/reject"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # create algorithm
        current_algorithm = Algorithm(status=AlgorithmStatus.APPROVED, image="image")
        current_algorithm.save()
        new_algorithm = Algorithm(status=AlgorithmStatus.UNDER_REVIEW, image="image")
        new_algorithm.save()

        # register server
        server = self.register_server()

        # check that rejecting a review without authentication fails
        response = self.app.post("/api/review/1/reject", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user allowed to reject reviews
        reviewer = self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        another_reviewer = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )

        # create reviews
        review = Review(
            status=ReviewStatus.UNDER_REVIEW, algorithm=new_algorithm, reviewer=reviewer
        )
        review.save()
        another_review = Review(
            status=ReviewStatus.UNDER_REVIEW,
            algorithm=new_algorithm,
            reviewer=another_reviewer,
        )
        another_review.save()

        # check that rejecting non-existing review fails
        response = self.app.post("/api/review/9999/reject", headers=HEADERS, json={})
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # check that rejecting review fails if it was already approved or rejected
        review.status = ReviewStatus.APPROVED
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/reject", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        review.status = ReviewStatus.REJECTED
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/reject", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that user cannot reject a review that is not assigned to them
        response = self.app.post(
            f"/api/review/{another_review.id}/reject", headers=HEADERS, json={}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # approve the second review so that the first one can be rejected with the
        # side-effects of the algorithm status being updated
        another_review.status = ReviewStatus.APPROVED
        another_review.save()

        # check that rejecting a review with authentication succeeds, and that the
        # algorithm status is updated to rejected
        body_ = {"comment": "Not good enough!"}
        review.status = ReviewStatus.UNDER_REVIEW
        review.save()
        response = self.app.post(
            f"/api/review/{review.id}/reject", headers=HEADERS, json=body_
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        review = Review.get(review.id)
        self.assertEqual(review.comment, body_["comment"])
        self.assertEqual(review.status, ReviewStatus.REJECTED.value)
        algorithm = Algorithm.get(new_algorithm.id)
        self.assertEqual(algorithm.status, AlgorithmStatus.REJECTED)
        # check also that old algorithm is still present
        current_algorithm = Algorithm.get(current_algorithm.id)
        self.assertEqual(current_algorithm.status, AlgorithmStatus.APPROVED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_algorithm_status_update_to_under_review(self, validate_token_mock):
        """Test that algorithm status is updated to under review if the minimum number of
        reviews and organizations are assigned"""

        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # register policy for minimum reviewers
        Policy(key=StorePolicies.MIN_REVIEWERS, value="2").save()

        # register policy for minimum reviewing organizations
        Policy(key=StorePolicies.MIN_REVIEWING_ORGANIZATIONS, value="2").save()

        # create algorithm
        algorithm = Algorithm(
            status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT, image="image"
        )
        algorithm.save()

        # register server
        server = self.register_server()

        # register user allowed to assign reviews
        reviewer_1 = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
            organization_id=1,
        )

        reviewer_2 = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_2,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
            organization_id=2,
        )

        reviewer_3 = self.register_user(
            server.id,
            username="reviewer_user_3",
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
            organization_id=1,
        )

        json_body = {
            "algorithm_id": algorithm.id,
            "reviewer_id": reviewer_1.id,
        }

        # register user allowed to create, delete and edit reviews
        self.register_user(
            server.id,
            username=USERNAME,
            user_rules=[
                Rule.get_by_("review", Operation.CREATE),
                Rule.get_by_("review", Operation.DELETE),
                Rule.get_by_("review", Operation.EDIT),
            ],
        )

        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # assign a review
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that the status did not change after the first assignment
        self.assertEqual(
            response.json["status"], AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        )

        # assign second reviewer
        json_body["reviewer_id"] = reviewer_2.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        review2_id = response.json["id"]
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that the status changed after the second assignment
        self.assertEqual(response.json["status"], AlgorithmStatus.UNDER_REVIEW.value)

        # delete a review and check that the status is back to awaiting reviewer assignment
        response = self.app.delete(f"/api/review/{review2_id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(
            response.json["status"], AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        )

        # assign a new reviewer from the same organization of the first one and check that
        # the status is still awaiting reviewer assignment
        json_body["reviewer_id"] = reviewer_3.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(
            response.json["status"], AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        )
        # assign a new reviewer from a different organization and check that
        # the status is now under review
        json_body["reviewer_id"] = reviewer_2.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        review_id = response.json["id"]
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json["status"], AlgorithmStatus.UNDER_REVIEW.value)

        # check that the status changes back to awaiting reviewer assignment if the reviewer
        # is removed, even if one of the reviews has been submitted.

        self.app.post(f"/api/review/{review_id}/approve", headers=HEADERS, json={})
        response = self.app.delete(f"/api/review/{review_id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.app.get(f"/api/algorithm/{algorithm.id}", headers=HEADERS)
        self.assertEqual(
            response.json["status"], AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        )

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_reviewer_assigners_policy(self, validate_token_mock):
        """Test that only users with the assign_review_own_algorithm policy can assign
        themselves to review an algorithm"""

        validate_token_mock.return_value = (
            MockResponse({"username": "assigner_user_2"}),
            HTTPStatus.OK,
        )

        # create algorithm
        algorithm = Algorithm(
            status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT, image="image"
        )
        algorithm.save()

        # register server
        server = self.register_server()

        # register users allowed to assign reviews
        reviewer_1 = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_1,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )

        reviewer_2 = self.register_user(
            server.id,
            username=REVIEWER_USERNAME_2,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )

        # register users allowed to create reviews
        self.register_user(
            server.id,
            username="assigner_user_1",
            user_rules=[Rule.get_by_("review", Operation.CREATE)],
        )

        assigner_2 = self.register_user(
            server.id,
            username="assigner_user_2",
            user_rules=[Rule.get_by_("review", Operation.CREATE)],
        )

        json_body = {
            "algorithm_id": algorithm.id,
            "reviewer_id": reviewer_1.id,
        }

        # register policy for allowed assigners
        reviewer_1_ref = f"{reviewer_1.username}|{reviewer_1.server.url}"
        Policy(key=StorePolicies.ALLOWED_REVIEWERS, value=reviewer_1_ref).save()

        # register policy for allowed reviewers
        Policy(key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS, value=reviewer_1_ref).save()

        # verify that the assigner 2 (returned by the mocked token validation)
        # cannot assign a review, as they are not in the allowed reviewers policy
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # add the assigner to the allowed reviewers policy and verify that
        # the assigner can now assign a review
        Policy(
            key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS,
            value=f"{assigner_2.username}|{assigner_2.server.url}",
        ).save()
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        # verify that a review cannot be assigned to a user that
        # is not in the allowed reviewers policy
        json_body["reviewer_id"] = reviewer_2.id
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # add the reviewer to the allowed reviewers policy and verify that
        # a review can now be assigned
        Policy(
            key=StorePolicies.ALLOWED_REVIEWERS,
            value=f"{reviewer_2.username}|{reviewer_2.server.url}",
        ).save()
        response = self.app.post("/api/review", headers=HEADERS, json=json_body)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)


if __name__ == "__main__":
    unittest.main()
