import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.backend.common import session
from vantage6.common.globals import Ports
from vantage6.algorithm.store.model.rule import Rule, Operation
from vantage6.algorithm.store.model.role import Role

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


class TestRoleResource(TestResources):
    """Test the role resource."""

    def setup_mock_and_server(self, validate_token_mock):
        """Helper method to setup mock and register server."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )
        return self.register_server(SERVER_URL)

    def check_unauthorized(self, method, url):
        """Helper method to test unauthorized access."""
        response = method(url, headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_roles_view_multi(self, validate_token_mock):
        """Test the roles view."""
        server = self.setup_mock_and_server(validate_token_mock)
        self.check_unauthorized(self.app.get, "/api/role")
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.VIEW)]
        )
        response = self.app.get("/api/role", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Role.get()))

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_roles_view_single(self, validate_token_mock):
        """Test the roles view."""
        server = self.setup_mock_and_server(validate_token_mock)
        role = Role(name="test_role")
        role.save()
        self.check_unauthorized(self.app.get, f"/api/role/{role.id}")
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.VIEW)]
        )
        response = self.app.get(f"/api/role/{role.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.app.get("/api/role/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_roles_create(self, validate_token_mock):
        """Test the roles create."""
        server = self.setup_mock_and_server(validate_token_mock)

        self.check_unauthorized(self.app.post, "/api/role")

        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.CREATE)]
        )

        valid_data = {"name": "test_role", "description": "A test role", "rules": []}
        response = self.app.post("/api/role", headers=HEADERS, json=valid_data)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        invalid_data = {"invalid_field": "value"}
        response = self.app.post("/api/role", headers=HEADERS, json=invalid_data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        invalid_rule = {
            "name": "test_role",
            "description": "A test role",
            "rules": [4],
        }
        response = self.app.post("/api/role", headers=HEADERS, json=invalid_rule)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_role_patch(self, validate_token_mock):
        server = self.setup_mock_and_server(validate_token_mock)
        role = Role(name="test_role")
        role.save()

        self.check_unauthorized(self.app.patch, f"/api/role/{role.id}")

        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.EDIT)]
        )

        valid_data = {"name": "test_role_updated", "description": "A test role"}
        response = self.app.patch(
            f"/api/role/{role.id}", headers=HEADERS, json=valid_data
        )
        session.session.refresh(role)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(role.name, valid_data["name"])
        self.assertEqual(role.description, valid_data["description"])

        invalid_rule = {
            "name": "test_role",
            "description": "A test role",
            "rules": [4],
        }
        response = self.app.patch(
            f"/api/role/{role.id}", headers=HEADERS, json=invalid_rule
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_role_delete(self, validate_token_mock):
        server = self.setup_mock_and_server(validate_token_mock)
        role = Role(name="test_role")
        role.save()

        self.check_unauthorized(self.app.delete, f"/api/role/{role.id}")

        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.DELETE)]
        )

        response = self.app.delete(f"/api/role/{role.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(Role.get(role.id))

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_role_delete_not_found(self, validate_token_mock):
        server = self.setup_mock_and_server(validate_token_mock)
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("role", Operation.DELETE)]
        )
        response = self.app.delete("/api/role/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_add_rule_to_role(self, validate_token_mock):
        server = self.setup_mock_and_server(validate_token_mock)
        rule = Rule.get_by_("role", Operation.EDIT)
        role = self.create_role(rules=[rule])

        self.check_unauthorized(self.app.post, f"/api/role/{role.id}/rule/9999")

        self.register_user(
            server.id,
            USERNAME,
            user_rules=[Rule.get_by_("role", Operation.EDIT)],
            user_roles=[role],
        )

        response = self.app.post(f"/api/role/{role.id}/rule/{rule.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(len(role.rules), 1)

        invalid_rule = Rule.get_by_("role", Operation.CREATE)
        response = self.app.post(
            f"/api/role/{role.id}/rule/{invalid_rule.id}", headers=HEADERS
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_delete_rule_from_role(self, validate_token_mock):
        server = self.setup_mock_and_server(validate_token_mock)
        rule = Rule.get_by_("role", Operation.EDIT)
        role = self.create_role(rules=[rule])

        self.check_unauthorized(self.app.delete, f"/api/role/{role.id}/rule/{rule.id}")

        self.register_user(
            server.id,
            USERNAME,
            user_rules=[Rule.get_by_("role", Operation.EDIT)],
            user_roles=[role],
        )

        response = self.app.delete(
            f"/api/role/{role.id}/rule/{rule.id}", headers=HEADERS
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(role.rules), 0)


if __name__ == "__main__":
    unittest.main()
