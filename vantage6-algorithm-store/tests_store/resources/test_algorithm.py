import datetime
import unittest
from http import HTTPStatus
from unittest.mock import patch

from vantage6.common.enum import (
    AlgorithmArgumentType,
    AlgorithmStepType,
    AlgorithmViewPolicies,
    StorePolicies,
)

from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.allowed_argument_value import AllowedArgumentValue
from vantage6.algorithm.store.model.argument import Argument
from vantage6.algorithm.store.model.common.enums import (
    AlgorithmStatus,
    Partitioning,
    ReviewStatus,
)
from vantage6.algorithm.store.model.database import Database
from vantage6.algorithm.store.model.function import Function
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.review import Review
from vantage6.algorithm.store.model.rule import Operation, Rule
from vantage6.algorithm.store.model.ui_visualization import UIVisualization
from vantage6.algorithm.store.resource.algorithm import AlgorithmBaseResource

from ..base.unittest_base import TestResources


class TestAlgorithmResources(TestResources):
    def test_view_algorithm_decorator_open(self):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        public.
        """
        # test if the endpoint is protected if no policies are defined and required
        # headers are included
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # Create a policy that allows viewing algorithms for everyone
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW.value,
            value=AlgorithmViewPolicies.PUBLIC.value,
        )
        policy.save()

        # test if the endpoint is accessible now
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # verify that viewing non-approved algorithms is not allowed, even with public
        # policy
        for arg in [
            "awaiting_reviewer_assignment",
            "under_review",
            "in_review_process",
            "invalidated",
        ]:
            result = self.app.get(f"/api/algorithm?{arg}=1")
            self.assertEqual(result.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        policy.delete()

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_view_algorithm_decorator_whitelisted(self, authenticate_mock):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        whitelisted.
        """
        # create policy
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW.value,
            value=AlgorithmViewPolicies.AUTHENTICATED.value,
        )
        policy.save()

        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        # test without required authorization header
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # if the user is authenticated, the endpoint should be accessible
        self.register_user(authenticate_mock=authenticate_mock, auth=True)
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # test if endpoint is not accessible if user is requesting non-approved
        # algorithms
        for arg in [
            "awaiting_reviewer_assignment",
            "under_review",
            "in_review_process",
            "invalidated",
        ]:
            rv = self.app.get(f"/api/algorithm?{arg}=1")
            self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # cleanup
        policy.delete()

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_view_algorithm_decorator_private(self, authenticate_mock):
        """
        Test the @with_permission_to_view_algorithms decorator when the policy is set to
        private.
        """
        # create resources
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW.value,
            value=AlgorithmViewPolicies.ONLY_WITH_EXPLICIT_PERMISSION.value,
        )
        policy.save()

        # test if the endpoint is protected if user is not authenticated
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # test if the endpoint is accessible if user is whitelisted but does not have
        # explicit permission to view algorithms
        user = self.register_user(authenticate_mock=authenticate_mock)
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # test if the endpoint is accessible if user is whitelisted and has explicit
        # permission to view algorithms
        user.rules = [Rule.get_by_("algorithm", Operation.VIEW)]
        user.save()
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        # cleanup
        policy.delete()
        user.delete()

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_algorithm_view_multi(self, authenticate_mock):
        """Test GET /api/algorithm"""

        # Create an algorithm
        algorithm = Algorithm(
            name="test_algorithm",
            status=AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value,
        )
        algorithm.save()

        # Create a policy that allows viewing algorithms for everyone
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW.value,
            value=AlgorithmViewPolicies.PUBLIC.value,
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
        rv = self.app.get("/api/algorithm")
        self.assertEqual(rv.status_code, HTTPStatus.OK)
        self.assertEqual(
            len(rv.json["data"]),
            num_approved,
        )

        # now approve the algorithm and verify that it is returned
        algorithm.status = AlgorithmStatus.APPROVED.value
        algorithm.save()
        result = self.app.get("/api/algorithm")
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json["data"]), num_approved + 1)

        # check that by authenticating we can see the awaiting_reviewer_assignment
        # algorithms
        algorithm.status = AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        algorithm.save()
        user = self.register_user(
            user_rules=[Rule.get_by_("algorithm", Operation.VIEW)],
            authenticate_mock=authenticate_mock,
        )
        result = self.app.get("/api/algorithm?awaiting_reviewer_assignment=1")
        self.assertEqual(result.status_code, HTTPStatus.OK)
        self.assertEqual(len(result.json["data"]), num_awaiting_review)

        # cleanup
        algorithm.delete()
        policy.delete()
        user.delete()

    def test_algorithm_view_single(self):
        """Test /api/algorithm/<id>"""

        # Create a policy that allows viewing algorithms for everyone
        policy = Policy(
            key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
        )
        policy.save()

        # Test when algorithm is not found
        response = self.app.get("/api/algorithm/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Create a mock algorithm
        algorithm = Algorithm(
            name="test_algorithm",
            description="Test algorithm",
            image="test_image",
            partitioning="horizontal",
            vantage6_version="1.0",
            code_url="https://github.com/test_algorithm",
            documentation_url="https://docs.test_algorithm.com",
            submission_comments="test_comments",
        )
        algorithm.save()

        # Test when algorithm is found
        response = self.app.get(f"/api/algorithm/{algorithm.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json["name"], "test_algorithm")
        self.assertEqual(response.json["description"], "Test algorithm")
        self.assertEqual(response.json["image"], "test_image")
        self.assertEqual(response.json["partitioning"], "horizontal")
        self.assertEqual(response.json["vantage6_version"], "1.0")
        self.assertEqual(response.json["code_url"], "https://github.com/test_algorithm")
        self.assertEqual(
            response.json["documentation_url"], "https://docs.test_algorithm.com"
        )
        self.assertEqual(response.json["submission_comments"], "test_comments")

        # Cleanup
        algorithm.delete()

    @patch("vantage6.algorithm.store.resource._authenticate")
    @patch(
        "vantage6.algorithm.store.resource.algorithm.AlgorithmBaseResource._get_image_digest"
    )
    def test_algorithm_create(self, get_image_digest_mock, authenticate_mock):
        """Test POST /api/algorithm"""
        get_image_digest_mock.return_value = "some-image", "some-digest"

        # test if the endpoint is protected if user is not authenticated
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        rv = self.app.post(
            "/api/algorithm",
            json={"name": "test_algorithm", "description": "test_description"},
        )
        self.assertEqual(rv.status_code, HTTPStatus.UNAUTHORIZED)

        # create user allowed to create algorithms
        user = self.register_user(
            username="my_user",
            user_rules=[Rule.get_by_("algorithm", Operation.CREATE)],
            authenticate_mock=authenticate_mock,
        )

        # check that incomplete input data returns 400
        rv = self.app.post("/api/algorithm", json={})
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        json_data = {
            "name": "test_algorithm",
            "description": "test_description",
            "partitioning": Partitioning.HORIZONTAL.value,
            "code_url": "https://my-url.com",
            "vantage6_version": "6.6.6",
            "image": "some-image",
            "submission_comments": "test_comments",
            "functions": [
                {
                    "name": "test_function",
                    "step_type": AlgorithmStepType.CENTRAL_COMPUTE.value,
                    "databases": [
                        {"name": "test_database", "description": "test_description"}
                    ],
                    "arguments": [
                        {
                            "name": "test_argument",
                            "type": AlgorithmArgumentType.STRING.value,
                            "allowed_values": ["A"],
                        }
                    ],
                    "ui_visualizations": [
                        {"name": "test_visualization", "type": "table"}
                    ],
                }
            ],
        }

        # test if the endpoint is accessible
        rv = self.app.post(
            "/api/algorithm",
            json=json_data,
        )
        self.assertEqual(rv.status_code, HTTPStatus.CREATED)
        self.assertEqual(rv.json["name"], "test_algorithm")
        self.assertEqual(rv.json["description"], "test_description")
        self.assertEqual(rv.json["partitioning"], Partitioning.HORIZONTAL.value)
        self.assertEqual(rv.json["code_url"], "https://my-url.com")
        self.assertEqual(rv.json["vantage6_version"], "6.6.6")
        self.assertEqual(rv.json["image"], "some-image")
        self.assertEqual(len(rv.json["functions"]), 1)
        self.assertEqual(rv.json["functions"][0]["name"], "test_function")
        self.assertEqual(rv.json["functions"][0]["step_type"], "central_compute")
        self.assertEqual(len(rv.json["functions"][0]["databases"]), 1)
        self.assertEqual(
            rv.json["functions"][0]["databases"][0]["name"], "test_database"
        )
        self.assertEqual(
            rv.json["functions"][0]["databases"][0]["description"], "test_description"
        )
        self.assertEqual(len(rv.json["functions"][0]["arguments"]), 1)
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["name"], "test_argument"
        )
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["type"],
            AlgorithmArgumentType.STRING.value,
        )

        self.assertEqual(
            len(rv.json["functions"][0]["arguments"][0]["allowed_values"]), 1
        )
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["allowed_values"][0]["value"], "A"
        )

        self.assertEqual(len(rv.json["functions"][0]["ui_visualizations"]), 1)
        self.assertEqual(
            rv.json["functions"][0]["ui_visualizations"][0]["name"],
            "test_visualization",
        )
        self.assertEqual(
            rv.json["functions"][0]["ui_visualizations"][0]["type"], "table"
        )

        self.assertEqual(rv.json["digest"], "some-digest")
        self.assertEqual(
            rv.json["status"], AlgorithmStatus.AWAITING_REVIEWER_ASSIGNMENT.value
        )
        self.assertEqual(rv.json["approved_at"], None)
        self.assertEqual(rv.json["invalidated_at"], None)
        self.assertNotEqual(rv.json["submitted_at"], None)
        self.assertEqual(rv.json["developer_id"], user.id)
        self.assertEqual(rv.json["submission_comments"], "test_comments")

        # test default values - first with wrong default value type
        json_data["functions"][0]["arguments"] = [
            {
                "name": "test_argument",
                "type": AlgorithmArgumentType.STRING.value,
                "has_default_value": True,
                "default_value": 1,
            }
        ]
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        # test default values - now with correct default value type
        json_data["functions"][0]["arguments"][0]["default_value"] = "test"
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["default_value"], "test"
        )

        # also check that default value can be null
        del json_data["functions"][0]["arguments"][0]["default_value"]
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.CREATED)
        self.assertEqual(rv.json["functions"][0]["arguments"][0]["default_value"], None)

        # test that arguments cannot have the same name
        json_data["functions"][0]["arguments"] = [
            {
                "name": "test",
                "type": AlgorithmArgumentType.STRING.value,
            },
            {
                "name": "test",
                "type": AlgorithmArgumentType.FLOAT.value,
            },
        ]
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        # test that conditional arguments are correctly created
        json_data["functions"][0]["arguments"] = [
            {
                "name": "dependent",
                "type": AlgorithmArgumentType.STRING.value,
                "has_default_value": True,
                "conditional_on": "conditional",
                "conditional_operator": "==",
                "conditional_value": "test",
            },
            {
                "name": "conditional",
                "type": AlgorithmArgumentType.STRING.value,
            },
        ]
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.CREATED)
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["conditional_on_id"],
            rv.json["functions"][0]["arguments"][1]["id"],
        )
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["conditional_operator"], "=="
        )
        self.assertEqual(
            rv.json["functions"][0]["arguments"][0]["conditional_value"], "test"
        )

        # test that there is an error if argument with conditional does not have a
        # default value
        json_data["functions"][0]["arguments"][0]["has_default_value"] = False
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

        # test that we get an error if conditions are circular
        json_data["functions"][0]["arguments"] = [
            {
                "name": "dependent",
                "type": AlgorithmArgumentType.STRING.value,
                "conditional_on": "conditional",
                "conditional_operator": "==",
                "conditional_value": "test",
            },
            {
                "name": "conditional",
                "type": AlgorithmArgumentType.STRING.value,
                "conditional_on": "dependent",
                "conditional_operator": "==",
                "conditional_value": "test",
            },
        ]
        rv = self.app.post("/api/algorithm", json=json_data)
        self.assertEqual(rv.status_code, HTTPStatus.BAD_REQUEST)

    @patch("vantage6.algorithm.store.resource._authenticate")
    @patch(
        "vantage6.algorithm.store.resource.algorithm.AlgorithmBaseResource._get_image_digest"
    )
    def test_algorithm_update(self, get_image_digest_mock, authenticate_mock):
        """Test PATCH /api/algorithm/<id>"""
        get_image_digest_mock.return_value = "some-image", "some-digest"

        # test unauthorized without user with permission to update algorithms
        self.register_user(authenticate_mock=authenticate_mock)
        response = self.app.patch("/api/algorithm/9999")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # get user with permission to update algorithms
        user = self.register_user(
            user_rules=[Rule.get_by_("algorithm", Operation.EDIT)],
            authenticate_mock=authenticate_mock,
        )

        # create an algorithm
        algorithm = Algorithm(
            name="test_algorithm",
            description="test_description",
            partitioning=Partitioning.HORIZONTAL.value,
            code_url="https://my-url.com",
            vantage6_version="6.6.6",
            image="some-image",
            developer_id=user.id,
            submission_comments="test_comments",
        )
        algorithm.save()

        # check that wrong input data returns 400
        response = self.app.patch(
            f"/api/algorithm/{algorithm.id}",
            json={"non-existing": True},
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that the algorithm is updated if providing correct data
        response = self.app.patch(
            f"/api/algorithm/{algorithm.id}", json={"description": "new_description"}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json["description"], "new_description")

        # check that algorithm cannot be updated if it is approved
        algorithm.status = AlgorithmStatus.APPROVED.value
        algorithm.approved_at = datetime.datetime.now(datetime.timezone.utc)
        algorithm.save()
        response = self.app.patch(
            f"/api/algorithm/{algorithm.id}", json={"description": "new_description"}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that algorithm cannot be updated if it is invalidated
        algorithm.invalidated_at = datetime.datetime.now(datetime.timezone.utc)
        algorithm.save()
        response = self.app.patch(
            f"/api/algorithm/{algorithm.id}", json={"description": "new_description"}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that algorithm cannot be updated if at least one review has been
        # completed
        algorithm.status = AlgorithmStatus.UNDER_REVIEW.value
        algorithm.invalidated_at = None
        algorithm.save()
        review = Review(
            algorithm_id=algorithm.id,
            reviewer_id=user.id,
            status=ReviewStatus.APPROVED.value,
        )
        review.save()
        response = self.app.patch(
            f"/api/algorithm/{algorithm.id}", json={"description": "new_description"}
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_algorithm_delete(self, authenticate_mock):
        """Test DELETE /api/algorithm/<id>"""

        # Test if endpoint is accessible without user
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        response = self.app.delete("/api/algorithm/9999")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # Create a mock algorithm
        algorithm = Algorithm(
            name="test_algorithm",
            functions=[
                Function(
                    name="test_function",
                    databases=[
                        Database(name="test_database", description="test_description"),
                    ],
                    arguments=[
                        Argument(
                            name="test_argument",
                            type_=AlgorithmArgumentType.STRING.value,
                            allowed_values=[AllowedArgumentValue(value="A")],
                        )
                    ],
                    ui_visualizations=[
                        UIVisualization(
                            name="test_visualization",
                        )
                    ],
                )
            ],
        )
        algorithm.save()
        func_id = algorithm.functions[0].id
        db_id = algorithm.functions[0].databases[0].id
        arg_id = algorithm.functions[0].arguments[0].id
        allowed_value_id = algorithm.functions[0].arguments[0].allowed_values[0].id
        vis_id = algorithm.functions[0].ui_visualizations[0].id

        # Test when user is not authenticated
        response = self.app.delete(f"/api/algorithm/{algorithm.id}")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # Register user in the store with permission to delete algorithms
        self.register_user(
            user_rules=[Rule.get_by_("algorithm", Operation.DELETE)],
            authenticate_mock=authenticate_mock,
        )

        # Test when algorithm is not found
        response = self.app.delete("/api/algorithm/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Test when algorithm is found
        response = self.app.delete(f"/api/algorithm/{algorithm.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        # check that resources inside the algorithm are also deleted
        self.assertEqual(Algorithm.get(algorithm.id), None)
        self.assertEqual(Function.get(func_id), None)
        self.assertEqual(Database.get(db_id), None)
        self.assertEqual(Argument.get(arg_id), None)
        self.assertEqual(AllowedArgumentValue.get(allowed_value_id), None)
        self.assertEqual(UIVisualization.get(vis_id), None)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_algorithm_invalidate(self, authenticate_mock):
        """Test PATCH /api/algorithm/<id>/invalidate"""

        # Test if endpoint is accessible without user
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        response = self.app.post("/api/algorithm/9999/invalidate")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # Create a mock algorithm
        algorithm = Algorithm(
            name="test_algorithm",
            reviews=[Review(status=ReviewStatus.UNDER_REVIEW.value)],
        )
        algorithm.save()
        review_id = algorithm.reviews[0].id

        # Test when user is not authorized
        self.register_user(authenticate_mock=authenticate_mock)
        response = self.app.post(f"/api/algorithm/{algorithm.id}/invalidate")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # Register user in the store with permission to invalidate algorithms
        self.register_user(
            user_rules=[Rule.get_by_("algorithm", Operation.DELETE)],
            authenticate_mock=authenticate_mock,
        )

        # Test when algorithm is not found
        response = self.app.post("/api/algorithm/9999/invalidate")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # Test when algorithm is found
        response = self.app.post(f"/api/algorithm/{algorithm.id}/invalidate")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        updated_algo = Algorithm.get(algorithm.id)
        self.assertEqual(updated_algo.status, AlgorithmStatus.REMOVED.value)
        self.assertNotEqual(updated_algo.invalidated_at, None)

        # check that the review is also dropped
        self.assertEqual(Review.get(review_id).status, ReviewStatus.DROPPED.value)

    @patch("vantage6.algorithm.store.resource.algorithm.get_digest")
    def test_get_image_digest(self, get_digest_mock):
        """Test AlgorithmBaseResource._get_image_digest"""
        # test that invalid image raises an error
        resource = AlgorithmBaseResource(None, None, None, None)

        # Test case 1: Image with digest found
        image_name = "example/image:latest"
        expected_image_wo_tag = "example/image"
        expected_digest = "some-digest"
        get_digest_mock.return_value = expected_digest

        # pylint: disable=protected-access
        image_wo_tag, digest = resource._get_image_digest(image_name)

        self.assertEqual(image_wo_tag, expected_image_wo_tag)
        self.assertEqual(digest, expected_digest)
        get_digest_mock.assert_called_once_with(image_name)

        # Test case 2: Image with digest not found on first call, with authentication
        # returned successfully
        registry = "docker.io"
        username = "user"
        password = "pass"
        docker_registry = [
            {"registry": registry, "username": username, "password": password}
        ]
        resource.config = {"docker_registries": docker_registry}

        get_digest_mock.reset_mock()
        get_digest_mock.side_effect = [None, expected_digest]

        image_wo_tag, digest = resource._get_image_digest(image_name)

        self.assertEqual(image_wo_tag, expected_image_wo_tag)
        self.assertEqual(digest, expected_digest)
        get_digest_mock.assert_any_call(image_name)
        get_digest_mock.assert_any_call(
            full_image=image_name,
            registry_username=username,
            registry_password=password,
        )

        # Test case 3: Image with digest not found, and no proper authentication details
        # provided
        docker_registry = [{"registry": "other-registry"}]
        resource.config = {"docker_registries": docker_registry}

        get_digest_mock.reset_mock()
        get_digest_mock.side_effect = [None]

        image_wo_tag, digest = resource._get_image_digest(image_name)

        self.assertEqual(image_wo_tag, expected_image_wo_tag)
        self.assertEqual(digest, None)
        get_digest_mock.assert_called_once_with(image_name)


if __name__ == "__main__":
    unittest.main()
