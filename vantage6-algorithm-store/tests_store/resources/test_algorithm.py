from http import HTTPStatus
import unittest
from unittest.mock import patch

from vantage6.algorithm.store.default_roles import DefaultRole
from vantage6.algorithm.store.model.common.enums import AlgorithmStatus, Partitioning

from ..base.unittest_base import MockResponse, TestResources
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.rule import Rule
from vantage6.common.enum import StorePolicies, AlgorithmViewPolicies

SERVER_URL = "http://localhost:5000"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


class TestAlgorithmResources(TestResources):

    def test_view_algorithm_decorator_open(self):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        public.
        """
        # test if the endpoint is protected if no policies are defined and required
        # headers are included
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.FORBIDDEN)

        # Create a policy that allows viewing algorithms for everyone
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
        )
        policy.save()

        # test if the endpoint is accessible now
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # verify that viewing non-approved algorithms is not allowed, even with public
        # policy
        for arg in [
            "awaiting_reviewer_assignment",
            "under_review",
            "in_review_process",
            "invalidated",
        ]:
            result = self.app.get(f"/api/algorithm?{arg}=1", headers=HEADERS)
            self.assertEqual(result.status_code, HTTPStatus.FORBIDDEN)

        # cleanup
        policy.delete()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_view_algorithm_decorator_whitelisted(self, validate_token_mock):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        whitelisted.
        """
        # create policy
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.WHITELISTED
        )
        policy.save()

        # test endpoint without required server-url header
        headers = {}
        rv = self.app.get("/api/algorithm", headers=headers)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        # test without required authorization header
        headers = {"server_url": SERVER_URL}
        rv = self.app.get("/api/algorithm", headers=headers)
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # Now use all required headers and test if the endpoint is protected if no
        # servers are whitelisted
        headers["Authorization"] = "mock"
        rv = self.app.get("/api/algorithm", headers=headers)
        self.assertEqual(rv.status_code, HTTPStatus.FORBIDDEN)

        # whitelist the server
        whitelisted_server = self.register_server()

        # verify returned status when server is not found
        validate_token_mock.return_value = MockResponse(), HTTPStatus.NOT_FOUND
        rv = self.app.get("/api/algorithm", headers=headers)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        # if token validation is successful, the endpoint should be accessible
        validate_token_mock.return_value = MockResponse(), HTTPStatus.OK
        rv = self.app.get("/api/algorithm", headers=headers)
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # cleanup
        policy.delete()
        whitelisted_server.delete()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_view_algorithm_decorator_private(self, validate_token_mock):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        private.
        """
        # create resources
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW,
            value=AlgorithmViewPolicies.ONLY_WITH_EXPLICIT_PERMISSION,
        )
        policy.save()
        whitelisted_server = self.register_server()

        # test if the endpoint is protected if user is not authenticated
        validate_token_mock.return_value = (
            MockResponse(),
            HTTPStatus.UNAUTHORIZED,
        )
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # test if the endpoint is protected if user authenticated but not whitelisted
        validate_token_mock.return_value = (
            MockResponse(json_data={"username": USERNAME}, status_code=HTTPStatus.OK),
            HTTPStatus.OK,
        )
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # test if the endpoint is accessible if user is whitelisted but does not have
        # explicit permission to view algorithms
        user = self.register_user(whitelisted_server.id)
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # test if the endpoint is accessible if user is whitelisted and has explicit
        # permission to view algorithms
        role = self.create_role([Rule.get_by_("algorithm", "view")])
        self.assign_role_to_user(user, role)
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # cleanup
        policy.delete()
        whitelisted_server.delete()
        user.delete()
        role.delete()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_algorithm_view(self, validate_token_mock):
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # Create an algorithm
        algorithm = Algorithm(
            name="test_algorithm", status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
        )
        algorithm.save()

        # Create a policy that allows viewing algorithms for everyone
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
        )
        policy.save()

        num_approved = len(
            [a for a in Algorithm.get() if a.status == AlgorithmStatus.APPROVED]
        )
        num_awaiting_review = len(
            [
                a
                for a in Algorithm.get()
                if a.status == AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
            ]
        )
        # test if the endpoint is accessible. Only approved algorithms should be
        # returned
        rv = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(rv.status_code, 200)
        self.assertEqual(
            len(rv.json["data"]),
            num_approved,
        )

        # now approve the algorithm and verify that it is returned
        algorithm.status = AlgorithmStatus.APPROVED
        algorithm.save()
        result = self.app.get("/api/algorithm", headers=HEADERS)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json["data"]), num_approved + 1)

        # check that by authenticating we can see the awaiting_reviewer_assignment
        # algorithms
        algorithm.status = AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT
        algorithm.save()
        user, server = self.register_user_and_server(username=USERNAME)
        role = self.create_role([Rule.get_by_("algorithm", "view")])
        self.assign_role_to_user(user, role)
        result = self.app.get(
            "/api/algorithm?awaiting_reviewer_assignment=1", headers=HEADERS
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json["data"]), num_awaiting_review)

        # cleanup
        algorithm.delete()
        policy.delete()
        server.delete()
        user.delete()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    @patch(
        "vantage6.algorithm.store.resource.algorithm.AlgorithmBaseResource._get_image_digest"
    )
    def test_algorithm_create(self, get_image_digest_mock, validate_token_mock):
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )
        get_image_digest_mock.return_value = "some-image", "some-digest"

        # test if the endpoint is accessible
        rv = self.app.post(
            "/api/algorithm",
            json={"name": "test_algorithm", "description": "test_description"},
            headers=HEADERS,
        )
        self.assertEqual(rv.status_code, 403)

        # create user allowed to create algorithms
        user, server = self.register_user_and_server(username=USERNAME)
        role = self.create_role([Rule.get_by_("algorithm", "create")])
        self.assign_role_to_user(user, role)

        # check that incomplete input data returns 400
        rv = self.app.post("/api/algorithm", json={}, headers=HEADERS)
        self.assertEqual(rv.status_code, 400)

        # test if the endpoint is accessible
        rv = self.app.post(
            "/api/algorithm",
            json={
                "name": "test_algorithm",
                "description": "test_description",
                "partitioning": Partitioning.HORIZONTAL,
                "code_url": "https://my-url.com",
                "vantage6_version": "6.6.6",
                "image": "some-image",
                "functions": [],
            },
            headers=HEADERS,
        )
        self.assertEqual(rv.status_code, 201)


if __name__ == "__main__":
    unittest.main()
