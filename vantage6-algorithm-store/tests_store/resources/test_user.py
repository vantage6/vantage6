import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources
from vantage6.algorithm.store.model.rule import Operation, Rule
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.user import User


class TestUserResource(TestResources):
    """Test the user resource."""

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_users_view_multi(self, authenticate_mock):
        """Test the users view."""
        self.register_user(authenticate_mock=authenticate_mock)

        # check that getting users without authentication fails
        response = self.app.get("/api/user")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            user_rules=[Rule.get_by_("user", Operation.VIEW)],
            authenticate_mock=authenticate_mock,
        )

        # check that getting users with authentication works
        response = self.app.get("/api/user")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(User.get()))

        reviewer_role = Role(
            name="test_role", rules=[Rule.get_by_("review", Operation.EDIT)]
        )
        reviewer_role.save()
        self.register_user("other-username", user_roles=[reviewer_role])
        # test filter by users with review permission
        response = self.app.get("/api/user?can_review=1")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)
        # test filter by role ID
        response = self.app.get(f"/api/user?role_id={reviewer_role.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_users_view_single(self, authenticate_mock):
        """Test the users view."""
        user = self.register_user(authenticate_mock=authenticate_mock)

        # check that getting users without authorization fails
        response = self.app.get(f"/api/user/{user.id}")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            user_rules=[Rule.get_by_("user", Operation.VIEW)],
            authenticate_mock=authenticate_mock,
        )

        # check that getting users with authentication works
        response = self.app.get(f"/api/user/{user.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that getting non-existing user fails
        response = self.app.get("/api/user/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch("vantage6.algorithm.store.resource._authenticate")
    @patch("vantage6.algorithm.store.resource.user.get_keycloak_id_for_user")
    def test_user_create(
        self,
        get_keycloak_id_for_user_mock,
        authenticate_mock,
    ):
        """Test the user create."""
        # Mock the keycloak admin client
        get_keycloak_id_for_user_mock.return_value = "test-keycloak-id"

        self.register_user(authenticate_mock=authenticate_mock)

        # test without authentication
        body_ = {"username": "new_user", "roles": []}
        response = self.app.post("/api/user", json=body_)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission and try again
        self.register_user(
            user_rules=[Rule.get_by_("user", Operation.CREATE)],
            authenticate_mock=authenticate_mock,
        )
        response = self.app.post("/api/user", json=body_)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json["username"], body_["username"])

        # ensure we cannot register the same user twice (they have the same keycloak_id)
        response = self.app.post("/api/user", json=body_)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # ensure we cannot register a user with more permissions then we have
        get_keycloak_id_for_user_mock.return_value = "other-test-keycloak-id"
        role = Role(rules=Rule.get())
        role.save()
        body_ = {
            "username": "yet_another_user",
            "roles": [role.id],
        }
        response = self.app.post("/api/user", json=body_)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_user_update(self, authenticate_mock):
        """Test the user update."""
        user = self.register_user(authenticate_mock=authenticate_mock)

        # check that updating users without authentication fails
        response = self.app.patch(f"/api/user/{user.id}")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        auth_user = self.register_user(
            user_rules=[Rule.get_by_("user", Operation.EDIT)],
            authenticate_mock=authenticate_mock,
        )

        # check that updating users with authentication works
        response = self.app.patch(f"/api/user/{user.id}", json={"roles": []})
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that updating non-existing user fails
        response = self.app.patch("/api/user/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # check that they cannot add roles to a user if the role contains permissions
        # they don't have
        role = Role(name="test_role", rules=Rule.get())
        role.save()
        response = self.app.patch(f"/api/user/{user.id}", json={"roles": [role.id]})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # check that you cannot delete roles from someone if you don't have the
        # permissions from that role yourself
        user.roles = [role]
        user.save()
        response = self.app.patch(f"/api/user/{user.id}", json={"roles": []})
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # check that you can't change your own roles
        response = self.app.patch(
            f"/api/user/{auth_user.id}", json={"roles": [role.id]}
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_user_delete(self, authenticate_mock):
        """Test the user delete."""
        user = self.register_user(authenticate_mock=authenticate_mock)

        # check that deleting users without authentication fails
        response = self.app.delete(f"/api/user/{user.id}")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            user_rules=[Rule.get_by_("user", Operation.DELETE)],
            authenticate_mock=authenticate_mock,
        )

        # check that deleting users with authentication works
        response = self.app.delete(f"/api/user/{user.id}")
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that deleting non-existing user fails
        response = self.app.delete("/api/user/9999")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
