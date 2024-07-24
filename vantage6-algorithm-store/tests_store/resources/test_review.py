from http import HTTPStatus
import unittest
from unittest.mock import patch

from tests_store.base.unittest_base import MockResponse, TestResources
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, ReviewStatus
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.rule import Rule, Operation

SERVER_URL = "http://localhost:5000"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"
REVIEWER_USERNAME = "reviewer_user"


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
            username=REVIEWER_USERNAME,
            user_rules=[Rule.get_by_("review", Operation.EDIT)],
        )
        another_reviewer = self.register_user(
            server.id,
            username="another_reviewer",
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
        json_body["reviewer_id"] = reviewer.id
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

        # check that if there are two reviews, one of which is approved and the other is
        # deleted, the algorithm status is updated to approved
        approved_review = Review(status=ReviewStatus.APPROVED, algorithm=algorithm)
        approved_review.save()
        # re-create review again
        review = Review(status=ReviewStatus.UNDER_REVIEW, algorithm=algorithm)
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
            username=REVIEWER_USERNAME,
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
            username=REVIEWER_USERNAME,
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


if __name__ == "__main__":
    unittest.main()
