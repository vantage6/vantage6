import unittest
from http import HTTPStatus
from unittest.mock import patch

from tests_store.base.unittest_base import TestResources
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule


class TestRuleResource(TestResources):
    """Test the rule resource."""

    @patch("vantage6.algorithm.store.resource._authenticate")
    def test_rules_view_multi(self, authenticate_mock):
        """Test the rules view."""

        # check that getting rules without authentication fails
        self.register_user(authenticate_mock=authenticate_mock, auth=False)
        response = self.app.get("/api/rule")
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)

        # register user that authenticates
        self.register_user(authenticate_mock=authenticate_mock)

        # check that getting rules with authentication works
        response = self.app.get("/api/rule?no_pagination=1")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), len(Rule.get()))

        # check that we can get the rules for a particular user
        random_rule = Rule.get()[0]
        random_role = Role(name="random_role", rules=[random_rule])
        user = self.register_user(user_roles=[random_role])
        response = self.app.get("/api/rule", query_string={"user_id": user.id})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(len(response.json["data"]), 1)


if __name__ == "__main__":
    unittest.main()
