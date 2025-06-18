import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources
from vantage6.backend.common import session
from vantage6.algorithm.store.model.rule import Rule, Operation
from vantage6.algorithm.store.model.role import Role


class TestRoleResource(TestResources):
    """Test the role resource."""

    def check_unauthorized(self, method, url):
        """Helper method to test unauthorized access."""
        response = method(url)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_roles_view_multi(self, authenticate_mock):
        """Test the roles view."""
        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.VIEW)],
            authenticate_mock=authenticate_mock,
        )
        response = self.app.get("/api/role")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Role.get()))

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_roles_view_single(self, authenticate_mock):
        """Test the roles view."""
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        role = Role(name="test_role")
        role.save()
        self.check_unauthorized(self.app.get, f"/api/role/{role.id}")
        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.VIEW)],
            authenticate_mock=authenticate_mock,
        )
        response = self.app.get(f"/api/role/{role.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        response = self.app.get("/api/role/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_roles_create(self, authenticate_mock):
        """Test the roles create."""

        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        self.check_unauthorized(self.app.post, "/api/role")

        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.CREATE)],
            authenticate_mock=authenticate_mock,
        )

        valid_data = {"name": "test_role", "description": "A test role", "rules": []}
        response = self.app.post("/api/role", json=valid_data)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

        invalid_data = {"invalid_field": "value"}
        response = self.app.post("/api/role", json=invalid_data)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        invalid_rule = {
            "name": "test_role",
            "description": "A test role",
            "rules": [4],
        }
        response = self.app.post("/api/role", json=invalid_rule)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_role_patch(self, authenticate_mock):
        role = Role(name="test_role")
        role.save()

        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        self.check_unauthorized(self.app.patch, f"/api/role/{role.id}")

        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.EDIT)],
            authenticate_mock=authenticate_mock,
        )

        valid_data = {"name": "test_role_updated", "description": "A test role"}
        response = self.app.patch(f"/api/role/{role.id}", json=valid_data)
        session.session.refresh(role)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(role.name, valid_data["name"])
        self.assertEqual(role.description, valid_data["description"])

        invalid_rule = {
            "name": "test_role",
            "description": "A test role",
            "rules": [4],
        }
        response = self.app.patch(f"/api/role/{role.id}", json=invalid_rule)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_role_delete(self, authenticate_mock):
        role = Role(name="test_role")
        role.save()

        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        self.check_unauthorized(self.app.delete, f"/api/role/{role.id}")

        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.DELETE)],
            authenticate_mock=authenticate_mock,
        )

        response = self.app.delete(f"/api/role/{role.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(Role.get(role.id))

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_role_delete_not_found(self, authenticate_mock):
        self.register_user(
            user_rules=[Rule.get_by_("role", Operation.DELETE)],
            authenticate_mock=authenticate_mock,
        )
        response = self.app.delete("/api/role/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
