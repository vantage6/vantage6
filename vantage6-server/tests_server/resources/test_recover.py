import logging
from http import HTTPStatus
from unittest.mock import patch

from vantage6.common import logger_name
from vantage6.server.model import (
    Rule,
    Organization,
)
from vantage6.server.model.rule import Scope, Operation
from .test_resource_base import TestResourceBase


logger = logger_name(__name__)
log = logging.getLogger(logger)


class TestResources(TestResourceBase):

    @patch("vantage6.server.resource.recover.ResetAPIKey._change_api_key_in_keycloak")
    def test_reset_api_key(self, mock_change_api_key_in_keycloak):
        mock_change_api_key_in_keycloak.return_value = "new_api_key"
        org = Organization(name="Test Organization")
        org.save()
        node = self.create_node(organization=org)

        rule = Rule.get_by_("node", Scope.ORGANIZATION, Operation.EDIT)
        headers = self.create_user_and_login(organization=org, rules=[rule])

        response = self.app.post(
            "/api/recover/node",
            headers=headers,
            json={"id": node.id},
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("api_key", response.json)

        # Test missing ID in the request body
        response = self.app.post(
            "/api/recover/node",
            headers=headers,
            json={},
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("errors", response.json)

        # Test node not found
        response = self.app.post(
            "/api/recover/node",
            headers=headers,
            json={"id": 9999},  # Non-existent node ID
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertEqual(response.json["msg"], "Node id=9999 is not found!")

        # Test unauthorized access
        headers = self.create_user_and_login()  # User without permissions
        response = self.app.post(
            "/api/recover/node",
            headers=headers,
            json={"id": node.id},
        )
        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(response.json["msg"], "You lack the permission to do that!")

        # Cleanup
        node.delete()
        org.delete()
