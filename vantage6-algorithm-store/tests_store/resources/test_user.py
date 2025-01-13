import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.common.globals import Ports
from vantage6.algorithm.store.model.rule import Operation, Rule
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.policy import Policy
from vantage6.common.enum import StorePolicies

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


class TestUserResource(TestResources):
    """Test the user resource."""

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_users_view_multi(self, validate_token_mock):
        """Test the users view."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)

        # check that getting users without authentication fails
        response = self.app.get("/api/user", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("user", Operation.VIEW)]
        )

        # check that getting users with authentication works
        response = self.app.get("/api/user", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(User.get()))

        reviewer_role = Role(
            name="test_role", rules=[Rule.get_by_("review", Operation.EDIT)]
        )
        reviewer_role.save()
        self.register_user(server.id, "other-username", user_roles=[reviewer_role])
        # test filter by users with review permission
        response = self.app.get("/api/user?can_review=1", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)
        # test filter by role ID
        response = self.app.get(
            f"/api/user?role_id={reviewer_role.id}", headers=HEADERS
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_users_view_single(self, validate_token_mock):
        """Test the users view."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)
        user = User(username="test_user")
        user.save()

        # check that getting users without authentication fails
        response = self.app.get(f"/api/user/{user.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("user", Operation.VIEW)]
        )

        # check that getting users with authentication works
        response = self.app.get(f"/api/user/{user.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that getting non-existing user fails
        response = self.app.get("/api/user/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    @patch("vantage6.algorithm.store.resource.user.request_from_store_to_v6_server")
    def test_user_create(
        self,
        request_mock,
        validate_token_mock,
    ):
        """Test the user create."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )
        request_mock.return_value = (
            MockResponse(
                status_code=HTTPStatus.OK,
                json_data={
                    "data": [{"id": 1, "username": "mock", "organization": {"id": 1}}]
                },
            ),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)

        # test without authentication
        body_ = {"username": "new_user", "roles": []}
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission and try again
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("user", Operation.CREATE)]
        )
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertEqual(response.json["username"], body_["username"])

        # ensure we cannot register the same user twice
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # ensure we cannot register a user with more permissions then we have
        role = Role(rules=Rule.get())
        role.save()
        body_ = {
            "username": "yet_another_user",
            "roles": [role.id],
        }
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # if there are policies precluding users from certain server to be created, user
        # from that server should not be created. Note that before, no policies were
        # set, and therefore when setting just one allowed server, only users from that
        # server should be allowed to be created.
        body_["roles"] = []
        policy = Policy(
            key=StorePolicies.ALLOWED_SERVERS.value, value="http://another_server.com"
        )
        policy.save()
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that we can still create users from the allowed server
        policy.value = SERVER_URL
        policy.save()
        response = self.app.post("/api/user", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_user_update(self, validate_token_mock):
        """Test the user update."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)
        user = User(username="test_user")
        user.save()

        # check that updating users without authentication fails
        response = self.app.patch(f"/api/user/{user.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        auth_user = self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("user", Operation.EDIT)]
        )

        # check that updating users with authentication works
        response = self.app.patch(
            f"/api/user/{user.id}", headers=HEADERS, json={"roles": []}
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that updating non-existing user fails
        response = self.app.patch("/api/user/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        # check that they cannot add roles to a user if the role contains permissions
        # they don't have
        role = Role(name="test_role", rules=Rule.get())
        role.save()
        response = self.app.patch(
            f"/api/user/{user.id}", headers=HEADERS, json={"roles": [role.id]}
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # check that you cannot delete roles from someone if you don't have the
        # permissions from that role yourself
        user.roles = [role]
        user.save()
        response = self.app.patch(
            f"/api/user/{user.id}", headers=HEADERS, json={"roles": []}
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # check that you can't change your own roles
        response = self.app.patch(
            f"/api/user/{auth_user.id}", headers=HEADERS, json={"roles": [role.id]}
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_user_delete(self, validate_token_mock):
        """Test the user delete."""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server(SERVER_URL)
        user = User(username="test_user")
        user.save()

        # check that deleting users without authentication fails
        response = self.app.delete(f"/api/user/{user.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user with appropriate permission
        self.register_user(
            server.id, USERNAME, user_rules=[Rule.get_by_("user", Operation.DELETE)]
        )

        # check that deleting users with authentication works
        response = self.app.delete(f"/api/user/{user.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        # check that deleting non-existing user fails
        response = self.app.delete("/api/user/9999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
