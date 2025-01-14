from http import HTTPStatus
import unittest
from unittest.mock import patch

from tests_store.base.unittest_base import MockResponse, TestResources
from vantage6.common.globals import Ports, DEFAULT_API_PATH
from vantage6.algorithm.store.model.common.enums import (
    BooleanPolicies,
    ListPolicies,
    PublicPolicies,
)
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.resource.policy import PoliciesBase
from vantage6.common.enum import AlgorithmViewPolicies, StorePolicies

ALLOWED_SERVER = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": ALLOWED_SERVER, "Authorization": "Mock"}
USERNAME = "test_user"


class TestPolicyResources(TestResources):
    """Test the policy resources"""

    def create_policies(self):
        """Create policies for testing"""
        # Create policies
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
            ),
            Policy(key=StorePolicies.ALLOWED_SERVERS, value=ALLOWED_SERVER),
            Policy(key=StorePolicies.ALLOW_LOCALHOST, value="True"),
            Policy(key=StorePolicies.MIN_REVIEWERS, value="2"),
            Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM, value="False"),
        ]
        # pylint: disable=expression-not-assigned
        [p.save() for p in policies]

    # note that the policies are already deleted in super().tearDown()

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_private_policies_view(self, mock_validate):
        """Test /api/policy"""
        self.create_policies()

        # check that getting policies without authentication fails with forbidden if
        # server is not whitelisted
        response = self.app.get("/api/policy", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check 401 if server is whitelisted but no authentication is provided
        mock_validate.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.UNAUTHORIZED,
        )
        server = self.register_server()
        response = self.app.get("/api/policy", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # check that getting policies with authentication succeeds
        mock_validate.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )
        self.register_user(server.id)
        response = self.app.get("/api/policy", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # Check that the policies are present and correct
        policies = response.json
        self.assertEqual(
            policies[StorePolicies.ALGORITHM_VIEW], AlgorithmViewPolicies.PUBLIC
        )
        self.assertEqual(policies[StorePolicies.ALLOWED_SERVERS], [ALLOWED_SERVER])
        self.assertEqual(policies[StorePolicies.ALLOW_LOCALHOST], True)

    def test_public_policies_view(self):
        """Test /api/policy/public"""
        self.create_policies()
        # Get the policies
        response = self.app.get("/api/policy/public")
        self.assertEqual(response.status_code, 200)

        # Check that the public policies are present and correct
        policies = response.json
        self.assertEqual(
            policies[PublicPolicies.ALGORITHM_VIEW], AlgorithmViewPolicies.PUBLIC
        )
        self.assertEqual(policies[PublicPolicies.ALLOWED_SERVERS], [ALLOWED_SERVER])

        # check that non-public policies are not present
        for policy in StorePolicies:
            if policy not in [p.value for p in PublicPolicies]:
                self.assertNotIn(policy, policies)

    def test_policies_to_dict(self):
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW.value,
                value=AlgorithmViewPolicies.PUBLIC,
            ),
            Policy(
                key=StorePolicies.ALLOWED_SERVERS.value,
                value=ALLOWED_SERVER + DEFAULT_API_PATH,
            ),
            Policy(key=StorePolicies.ALLOW_LOCALHOST.value, value="1"),
        ]
        include_defaults = True
        include_private = False

        resource = PoliciesBase(None, None, None, None)
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )

        expected_dict = {
            "algorithm_view": "public",
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "allow_localhost": True,
        }
        self.assertEqual(response_dict, expected_dict)

    def test_policies_to_dict_with_defaults(self):
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW.value,
                value=AlgorithmViewPolicies.PUBLIC,
            ),
            Policy(
                key=StorePolicies.ALLOWED_SERVERS.value,
                value=ALLOWED_SERVER + DEFAULT_API_PATH,
            ),
            Policy(key=StorePolicies.MIN_REVIEWERS.value, value=2),
            Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value, value="False"),
            Policy(key=StorePolicies.MIN_REVIEWING_ORGANIZATIONS.value, value=2),
            Policy(key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value, value=1),
            Policy(key=StorePolicies.ALLOWED_REVIEWERS.value, value=1),
        ]
        include_defaults = True
        include_private = False

        resource = PoliciesBase(None, None, None, None)
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )

        expected_dict = {
            "algorithm_view": AlgorithmViewPolicies.PUBLIC,
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "min_reviewers": 2,
            "assign_review_own_algorithm": False,
            "min_reviewing_organizations": 2,
            "allowed_review_assigners": 1,
            "allowed_reviewers": 1,
        }
        self.assertEqual(response_dict, expected_dict)

        # check that private policies are included if include_private is True
        include_private = True
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )
        expected_dict = {
            "algorithm_view": AlgorithmViewPolicies.PUBLIC,
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "allow_localhost": False,
            "min_reviewers": 2,
            "assign_review_own_algorithm": False,
            "min_reviewing_organizations": 2,
            "allowed_review_assigners": 1,
            "allowed_reviewers": 1,
        }
        self.assertEqual(response_dict, expected_dict)

    def test_policies_to_dict_with_private_policies(self):
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
            ),
            Policy(
                key=StorePolicies.ALLOWED_SERVERS,
                value=ALLOWED_SERVER + DEFAULT_API_PATH,
            ),
            Policy(key=StorePolicies.ALLOW_LOCALHOST, value="1"),
            Policy(key=StorePolicies.MIN_REVIEWERS.value, value=2),
            Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value, value="False"),
            Policy(key=StorePolicies.MIN_REVIEWING_ORGANIZATIONS.value, value=2),
            Policy(key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value, value=1),
            Policy(key=StorePolicies.ALLOWED_REVIEWERS.value, value=1),
        ]
        include_defaults = True
        include_private = True

        resource = PoliciesBase(None, None, None, None)
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )

        expected_dict = {
            "algorithm_view": AlgorithmViewPolicies.PUBLIC,
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "allow_localhost": True,
            "min_reviewers": 2,
            "assign_review_own_algorithm": False,
            "min_reviewing_organizations": 2,
            "allowed_review_assigners": 1,
            "allowed_reviewers": 1,
        }

        self.assertEqual(response_dict, expected_dict)

    def test_policies_to_dict_with_boolean_policies(self):
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
            ),
            Policy(
                key=StorePolicies.ALLOWED_SERVERS,
                value=ALLOWED_SERVER + DEFAULT_API_PATH,
            ),
            Policy(key=BooleanPolicies.ALLOW_LOCALHOST, value="1"),
            Policy(key=StorePolicies.MIN_REVIEWERS.value, value=2),
            Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value, value="0"),
            Policy(key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value, value=1),
            Policy(key=StorePolicies.ALLOWED_REVIEWERS.value, value=1),
        ]
        include_defaults = True
        include_private = False

        resource = PoliciesBase(None, None, None, None)
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )

        expected_dict = {
            "algorithm_view": AlgorithmViewPolicies.PUBLIC,
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "allow_localhost": True,
            "min_reviewers": 2,
            "assign_review_own_algorithm": False,
            "allowed_review_assigners": 1,
            "allowed_reviewers": 1,
        }

        self.assertEqual(response_dict, expected_dict)

    def test_policies_to_dict_with_list_policies(self):
        policies = [
            Policy(
                key=StorePolicies.ALGORITHM_VIEW, value=AlgorithmViewPolicies.PUBLIC
            ),
            Policy(
                key=ListPolicies.ALLOWED_SERVERS,
                value=ALLOWED_SERVER + DEFAULT_API_PATH,
            ),
            Policy(key=StorePolicies.ALLOW_LOCALHOST, value="1"),
            Policy(key=StorePolicies.MIN_REVIEWERS.value, value=2),
            Policy(key=StorePolicies.ASSIGN_REVIEW_OWN_ALGORITHM.value, value="False"),
            Policy(key=StorePolicies.ALLOWED_REVIEW_ASSIGNERS.value, value=1),
            Policy(key=StorePolicies.ALLOWED_REVIEWERS.value, value=1),
        ]
        include_defaults = True
        include_private = False

        resource = PoliciesBase(None, None, None, None)
        response_dict = resource.policies_to_dict(
            policies, include_defaults, include_private
        )

        expected_dict = {
            "algorithm_view": AlgorithmViewPolicies.PUBLIC,
            "allowed_servers": [ALLOWED_SERVER + DEFAULT_API_PATH],
            "allow_localhost": True,
            "min_reviewers": 2,
            "assign_review_own_algorithm": False,
            "allowed_review_assigners": 1,
            "allowed_reviewers": 1,
        }

        self.assertEqual(response_dict, expected_dict)


if __name__ == "__main__":
    unittest.main()
