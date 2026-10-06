import logging
from unittest import TestCase, main
from unittest.mock import MagicMock, patch

from vantage6.common.client.node_client import NodeClient
from vantage6.common.globals import HQ_AUDIENCE_SCOPE, STORE_AUDIENCE_SCOPE


class TestTokens(TestCase):
    """HQ and algorithm stores each get their own token"""

    def setUp(self):
        self.client = object.__new__(NodeClient)
        self.client.log = logging.getLogger(__name__)

    def test_obtain_new_token_gets_token_per_audience(self):
        self.client.kc_openid = MagicMock()
        self.client.kc_openid.token.side_effect = lambda grant_type, scope: {
            "access_token": f"token-for-{scope}"
        }
        self.client.kc_openid.decode_token.return_value = {"exp": 300, "iat": 0}

        self.client.obtain_new_token()

        self.assertEqual(self.client._access_token, f"token-for-{HQ_AUDIENCE_SCOPE}")
        self.assertEqual(
            self.client._store_access_token, f"token-for-{STORE_AUDIENCE_SCOPE}"
        )

    @patch("vantage6.common.client.client_base.requests.get")
    def test_request_sends_matching_token(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {}
        self.client._access_token = "hq-token"
        self.client._store_access_token = "store-token"
        self.client.store = MagicMock(uses_hq_keycloak=True)

        with (
            patch.object(NodeClient, "generate_path_to", return_value="http://x"),
            patch.object(
                NodeClient,
                "_ClientBase__check_algorithm_store_valid",
                return_value=True,
            ),
        ):
            self.client.request("node/me")
            hq_headers = mock_get.call_args.kwargs["headers"]
            self.client.request("algorithm", is_for_algorithm_store=True)
            store_headers = mock_get.call_args.kwargs["headers"]
            # a store with its own Keycloak gets no token
            self.client.store.uses_hq_keycloak = False
            self.client.request("algorithm", is_for_algorithm_store=True)
            other_store_headers = mock_get.call_args.kwargs["headers"]

        self.assertEqual(hq_headers, {"Authorization": "Bearer hq-token"})
        self.assertEqual(store_headers, {"Authorization": "Bearer store-token"})
        self.assertEqual(other_store_headers, {})


class TestCheckUserAllowedToSendTask(TestCase):
    """Test check_user_allowed_to_send_task handles paginated API responses."""

    @classmethod
    def setUpClass(cls):
        # Create a client without calling __init__ (avoids needing credentials)
        cls.client = object.__new__(NodeClient)
        cls.client.log = logging.getLogger(__name__)

    def test_org_id_match_returns_true(self):
        """Matching org by ID should return True without an API call."""
        with patch.object(self.client.__class__, "request") as mock_request:
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[],
                allowed_orgs=["7"],
                init_org_id=7,
                init_user_id=1,
            )
        self.assertTrue(result)
        mock_request.assert_not_called()

    def test_org_name_match_with_paginated_response(self):
        """Matching org by name should work with the paginated API response."""
        with patch.object(
            self.client.__class__,
            "request",
            return_value={"data": [{"name": "TestOrg", "id": 7}], "links": {}},
        ):
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[],
                allowed_orgs=["TestOrg"],
                init_org_id=7,
                init_user_id=1,
            )
        self.assertTrue(result)

    def test_org_name_no_match_returns_false(self):
        """Non-matching org name should return False."""
        with patch.object(
            self.client.__class__,
            "request",
            return_value={"data": [{"name": "OtherOrg", "id": 9}], "links": {}},
        ):
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[],
                allowed_orgs=["TestOrg"],
                init_org_id=7,
                init_user_id=1,
            )
        self.assertFalse(result)

    def test_user_id_match_returns_true(self):
        """Matching user by ID should return True."""
        with patch.object(self.client.__class__, "request") as mock_request:
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=["42"],
                allowed_orgs=[],
                init_org_id=7,
                init_user_id=42,
            )
        self.assertTrue(result)
        mock_request.assert_not_called()

    def test_int_org_id_from_config_matches(self):
        """Org IDs written as ints in the config file should match (issue #1218)."""
        with patch.object(self.client.__class__, "request") as mock_request:
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[],
                allowed_orgs=[7],
                init_org_id=7,
                init_user_id=1,
            )
        self.assertTrue(result)
        mock_request.assert_not_called()

    def test_int_user_id_from_config_matches(self):
        """User IDs written as ints in the config file should match."""
        with patch.object(self.client.__class__, "request") as mock_request:
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[2],
                allowed_orgs=[],
                init_org_id=7,
                init_user_id=2,
            )
        self.assertTrue(result)
        mock_request.assert_not_called()

    def test_error_response_denies_task(self):
        """An error response should deny the task rather than raise."""
        with patch.object(
            self.client.__class__, "request", return_value={"msg": "Unauthorized"}
        ):
            result = self.client.check_user_allowed_to_send_task(
                allowed_users=[],
                allowed_orgs=["TestOrg"],
                init_org_id=7,
                init_user_id=1,
            )
        self.assertFalse(result)


if __name__ == "__main__":
    main()
