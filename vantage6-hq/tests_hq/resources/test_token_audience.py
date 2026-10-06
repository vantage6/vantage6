from http import HTTPStatus
from unittest.mock import patch
from uuid import uuid1

import jwt

from vantage6.common.globals import STORE_TOKEN_AUDIENCE

from vantage6.hq.model import AlgorithmStore, Rule, User
from vantage6.hq.resource.common.task_post_base import TaskPostBase

from .test_resource_base import MOCK_PRIVATE_KEY_PEM, TestResourceBase


class TestTokenAudience(TestResourceBase):
    def test_tokens_for_stores_refused(self):
        """HQ refuses tokens issued for algorithm stores, including HQ's own"""
        user = User(username=str(uuid1()), rules=Rule.get(), keycloak_id=str(uuid1()))
        user.save()

        rv = self.app.get("/api/user", headers=self.login(user))
        self.assertEqual(rv.status_code, HTTPStatus.OK)

        rv = self.app.get(
            "/api/user", headers=self.login(user, audience=STORE_TOKEN_AUDIENCE)
        )
        self.assertNotEqual(rv.status_code, HTTPStatus.OK)

        hq_token = jwt.encode(
            {
                "sub": str(uuid1()),
                "vantage6_client_type": "hq",
                "aud": STORE_TOKEN_AUDIENCE,
                "exp": 9999999999,
                "iat": 0,
            },
            MOCK_PRIVATE_KEY_PEM,
            algorithm="RS256",
        )
        rv = self.app.get("/api/user", headers={"Authorization": f"Bearer {hq_token}"})
        self.assertNotEqual(rv.status_code, HTTPStatus.OK)

    @patch("vantage6.hq.resource.common.task_post_base.get_hq_token_for_stores")
    @patch("vantage6.hq.resource.common.task_post_base.request_algo_store")
    def test_store_lookup_uses_hq_token(self, request_algo_store, get_token):
        """
        The algorithm lookup at the store uses HQ's token, never the user's, and only
        for stores that use HQ's Keycloak
        """
        get_token.return_value = "hq-token"
        response = type("R", (), {"json": lambda self: {"data": [{"id": 1}]}})()
        request_algo_store.return_value = (response, HTTPStatus.OK)

        for uses_hq_keycloak, expected_headers in [
            (True, {"Authorization": "Bearer hq-token"}),
            (False, {}),
        ]:
            store = AlgorithmStore(
                url="http://store", api_path="/api", uses_hq_keycloak=uses_hq_keycloak
            )
            with self.server.app.test_request_context(
                headers={"Authorization": "Bearer user-token"}
            ):
                algorithm = TaskPostBase._get_algorithm_from_store(
                    store=store, image="some-image"
                )

            self.assertEqual(algorithm, {"id": 1})
            headers = request_algo_store.call_args.kwargs["headers"]
            self.assertEqual(headers, expected_headers)
