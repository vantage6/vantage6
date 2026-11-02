from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import jwt

from vantage6.hq.model import Collaboration, Organization
from vantage6.hq.websockets import DefaultSocketNamespace

from .test_resource_base import TestResourceBase

MODULE = "vantage6.hq.websockets"


class TestSocketConnectAuthentication(TestResourceBase):
    """Clients that fail to authenticate on the socket must be disconnected."""

    def _connect(self, verify_side_effect=None, identity="unknown-keycloak-id"):
        namespace = DefaultSocketNamespace("/tasks", MagicMock(), MagicMock())
        socket_session = SimpleNamespace()
        with (
            patch(f"{MODULE}.verify_jwt_in_request", side_effect=verify_side_effect),
            patch(f"{MODULE}.get_jwt_identity", return_value=identity),
            patch(f"{MODULE}.request", MagicMock(sid="test-sid")),
            patch(f"{MODULE}.session", socket_session),
            patch(f"{MODULE}.emit") as emit,
            patch(f"{MODULE}.join_room"),
            patch(f"{MODULE}.disconnect") as disconnect,
        ):
            namespace.on_connect()
        return emit, disconnect, socket_session

    def test_expired_token_is_disconnected(self):
        emit, disconnect, _ = self._connect(jwt.exceptions.ExpiredSignatureError())
        emit.assert_called_once_with("expired_token", room="test-sid")
        disconnect.assert_called_once()

    def test_invalid_signature_is_disconnected(self):
        emit, disconnect, _ = self._connect(jwt.exceptions.InvalidSignatureError())
        emit.assert_called_once_with("invalid_token", room="test-sid")
        disconnect.assert_called_once()

    def test_missing_token_is_disconnected(self):
        _, disconnect, socket_session = self._connect(RuntimeError("no token"))
        disconnect.assert_called_once()
        self.assertFalse(hasattr(socket_session, "auth_id"))

    def test_unknown_identity_is_disconnected(self):
        _, disconnect, socket_session = self._connect(identity="does-not-exist")
        disconnect.assert_called_once()
        self.assertFalse(hasattr(socket_session, "auth_id"))

    def test_valid_node_is_not_disconnected(self):
        org = Organization()
        col = Collaboration(organizations=[org])
        node = self.create_node(organization=org, collaboration=col)

        _, disconnect, socket_session = self._connect(identity=node.keycloak_id)

        disconnect.assert_not_called()
        self.assertEqual(socket_session.auth_id, node.keycloak_id)
        self.assertEqual(socket_session.type, "node")
