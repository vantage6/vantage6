import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.common.globals import Ports
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


class TestRuleResource(TestResources):
    """Test the rule resource."""

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_rules_view_multi(self, validate_token_mock):
        """Test the rules view."""

        server = self.register_server(SERVER_URL)

        # check that getting rules without authentication fails
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.UNAUTHORIZED,
        )
        response = self.app.get("/api/rule", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # check that getting rules with authentication works
        response = self.app.get("/api/rule?no_pagination=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Rule.get()))

        # check that we can get the rules for a particular user
        random_rule = Rule.get()[0]
        random_role = Role(name="random_role", rules=[random_rule])
        user = self.register_user(server.id, USERNAME, user_roles=[random_role])
        response = self.app.get(
            "/api/rule",
            query_string={"username": user.username, "server_url": server.url},
            headers=HEADERS,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)


if __name__ == "__main__":
    unittest.main()
