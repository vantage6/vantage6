from unittest import TestCase, main
from unittest.mock import patch

from vantage6.common.client.node_client import NodeClient


class TestCheckUserAllowedToSendTask(TestCase):
    """Test check_user_allowed_to_send_task handles paginated API responses."""

    @classmethod
    def setUpClass(cls):
        # Create a client without calling __init__ (avoids needing credentials)
        cls.client = object.__new__(NodeClient)

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


if __name__ == "__main__":
    main()
