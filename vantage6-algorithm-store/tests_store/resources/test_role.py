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

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    @patch("vantage6.algorithm.store.resource.role.validate_request_body")
    @patch("vantage6.algorithm.store.resource.role.get_rules")
    def test_role_create(
        self, get_rules_mock, validate_request_body_mock, validate_token_mock
    ):
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )
        validate_request_body_mock.return_value = None
        get_rules_mock.return_value = []

        server = self.register_server(SERVER_URL)

        response = self.app.post("/api/role", headers=HEADERS, json={})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.CREATE)]
        )

        valid_data = {"name": "test_role", "description": "A test role"}
        response = self.app.post("/api/role", headers=HEADERS, json=valid_data)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIn("name", response.json)
        self.assertEqual(response.json["name"], valid_data["name"])

        validate_request_body_mock.return_value = {"msg": "Invalid data"}
        invalid_data = {"invalid_field": "value"}
        response = self.app.post("/api/role", headers=HEADERS, json=invalid_data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("msg", response.json)
        self.assertEqual(response.json["msg"], "Invalid data")


if __name__ == "__main__":
    unittest.main()
