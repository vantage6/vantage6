""" " Test /vantage6-server endpoints"""

import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.common.globals import Ports
from vantage6.algorithm.store.default_roles import DefaultRole
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.rule import Operation, Rule
from vantage6.algorithm.store.model.user import User
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.common.enum import StorePolicies

SERVER_URL = f"http://localhost:{Ports.DEV_SERVER.value}"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"
EMAIL = "test@email.org"
ORGANIZATION_ID = 1


class TestVantage6ServerResource(TestResources):
    """Test the rule resource."""

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_server_view_multi(self, validate_token_mock):
        """Test GET /vantage6-server"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.UNAUTHORIZED,
        )
        server = Vantage6Server(url=SERVER_URL)
        server.save()

        # check that getting servers without authentication fails
        response = self.app.get("/api/vantage6-server", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # now mock that the user is authenticated
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # check that getting servers with authentication works
        response = self.app.get("/api/vantage6-server", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json), len(Vantage6Server.get()))

        # test if filtering by server URL works
        other_server = Vantage6Server(url="http://my-server.com")
        other_server.save()
        response = self.app.get(
            "/api/vantage6-server",
            headers=HEADERS,
            query_string={"url": other_server.url},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json), 1)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_server_view_single(self, validate_token_mock):
        """Test GET /vantage6-server/<id>"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.UNAUTHORIZED,
        )
        server = Vantage6Server(url=SERVER_URL)
        server.save()

        # check that getting servers without authentication fails
        response = self.app.get(f"/api/vantage6-server/{server.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # now mock that the user is authenticated
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        # check that getting servers with authentication works
        response = self.app.get(f"/api/vantage6-server/{server.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json["id"], server.id)

        # check that non-existing server fails
        response = self.app.get("/api/vantage6-server/99999", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    @patch(
        "vantage6.algorithm.store.resource.vantage6_server"
        ".request_validate_server_token"
    )
    def test_server_create(self, validate_token_mock):
        """Test POST /vantage6-server"""
        # Note that this endpoint needs no authentication, but should comply with the
        # policies set in the database

        # create policy that only allows one server
        policy = Policy(key=StorePolicies.ALLOWED_SERVERS, value="https://server.com")
        policy.save()

        self.register_user_and_server()

        # ensure default roles are created - a role is assigned to the user when they
        # whitelist the server
        self.create_default_roles()

        # check that creating a different server fails
        body_ = {"url": "http://another-server.com"}
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that creating whitelisted server doesn't work if the server does not
        # successfully verify the user
        body_ = {"url": "https://server.com"}
        validate_token_mock.return_value = (
            MockResponse({}, status_code=HTTPStatus.NOT_FOUND),
            HTTPStatus.NOT_FOUND,
        )
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that creating this server works
        validate_token_mock.return_value = (
            MockResponse(
                {
                    "username": USERNAME,
                    "email": EMAIL,
                    "organization_id": ORGANIZATION_ID,
                },
                status_code=HTTPStatus.OK,
            ),
            HTTPStatus.OK,
        )
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.CREATED)
        self.assertIsNotNone(response.json["id"])
        # check that a user exists for this server with the current username and the
        # server manager role
        server_manager = User.get_by_server(USERNAME, response.json["id"])
        self.assertIsNotNone(server_manager)
        self.assertEqual(server_manager.roles[0].name, DefaultRole.SERVER_MANAGER)

        # if we try this again it should fail
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.ALREADY_REPORTED)

        # check that whitelisting localhost servers cannot be done with default policy
        policy.delete()
        body_ = {"url": "http://localhost:12345"}
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # check that whitelisting localhost still doesn't work without force
        policy = Policy(key=StorePolicies.ALLOW_LOCALHOST, value="1")
        policy.save()
        response = self.app.post("/api/vantage6-server", headers=HEADERS, json=body_)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

        # check that whitelisting localhost works with force
        body_["force"] = True
        response = self.app.post(
            "/api/vantage6-server",
            headers=HEADERS,
            json=body_,
        )
        self.assertEqual(response.status_code, HTTPStatus.CREATED)

    @patch("vantage6.algorithm.store.resource.request_validate_server_token")
    def test_server_delete(self, validate_token_mock):
        """Test DELETE /vantage6-server/<id>"""
        validate_token_mock.return_value = (
            MockResponse({"username": USERNAME}),
            HTTPStatus.OK,
        )

        server = self.register_server()

        # check that deleting a server without permission fails
        response = self.app.delete(f"/api/vantage6-server/{server.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # removing someone else's server should fail
        user = self.register_user(
            server_id=server.id,
            user_rules=[Rule.get_by_("vantage6_server", Operation.DELETE)],
        )
        user_id = user.id
        other_server = Vantage6Server(url="http://other-server.com")
        other_server.save()
        response = self.app.delete(
            f"/api/vantage6-server/{other_server.id}", headers=HEADERS
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

        # now try removing own server with user that has permission
        response = self.app.delete(f"/api/vantage6-server/{server.id}", headers=HEADERS)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIsNone(Vantage6Server.get(server.id))
        self.assertIsNone(User.get(user_id))


if __name__ == "__main__":
    unittest.main()
