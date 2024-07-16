"""" Test /vantage6-server endpoints"""

import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources, MockResponse
from vantage6.algorithm.store.model.policy import Policy
from vantage6.algorithm.store.model.vantage6_server import Vantage6Server
from vantage6.common.enum import StorePolicies

SERVER_URL = "http://localhost:5000"
HEADERS = {"server_url": SERVER_URL, "Authorization": "Mock"}
USERNAME = "test_user"


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

    # def test_server_create(self):
    #     """Test POST /vantage6-server"""
    #     # Note that this endpoint needs no authentication, but should comply with the
    #     # policies set in the database

    #     # create policy that only allows one server
    #     policy = Policy(key=StorePolicies.ALLOWED_SERVERS, value="https://server.com")

    #     # check that creating a different server fails
    #     body_ = {"url": "http://my-server.com"}
    #     response = self.app.post("/api/vantage6-server", headers=HEADERS)
    #     self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

    #     # check that creating a server with authentication works
    #     response = self.app.post("/api/vantage6-server", headers=HEADERS)
    #     self.assertEqual(response.status_code, HTTPStatus.CREATED)
    #     self.assertIsNotNone(response.json["id"])


if __name__ == "__main__":
    unittest.main()
