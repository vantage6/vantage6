import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.common.globals import Ports
from vantage6.algorithm.store.model.rule import Rule, Operation
from vantage6.algorithm.store.model.role import Role

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


class TestRoleResource(TestResources):
    """Test the role resource."""

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_roles_view_multi(self, validate_token_mock):
        """Test the roles view."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)

        # check that getting roles without authentication fails
        response = self.app.get("/api/role", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.VIEW)]
        )

        # check that getting roles with authentication works
        response = self.app.get("/api/role", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Role.get()))

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_roles_view_single(self, validate_token_mock):
        """Test the roles view."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)
        role = Role(name="test_role")
        role.save()

        # check that getting roles without authentication fails
        response = self.app.get(f"/api/role/{role.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.VIEW)]
        )

        # check that getting roles with authentication works
        response = self.app.get(f"/api/role/{role.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that getting non-existing role fails
        response = self.app.get("/api/role/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
