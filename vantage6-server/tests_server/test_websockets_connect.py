import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import uuid1

import jwt

from vantage6.server.model import Collaboration, Node, Organization
from vantage6.server.model.base import Database, DatabaseSessionManager
from vantage6.server.websockets import DefaultSocketNamespace

MODULE = "vantage6.server.websockets"


class TestSocketConnectAuthentication(unittest.TestCase):
    """Clients that fail to authenticate on the socket must be disconnected."""

    def setUp(self):
        Database().connect("sqlite://", allow_drop_all=True)
        DatabaseSessionManager.get_session()

    def tearDown(self):
        Database().clear_data()

    def _connect(self, verify_side_effect=None, identity=999999):
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
        _, disconnect, socket_session = self._connect(identity=999999)
        disconnect.assert_called_once()
        self.assertFalse(hasattr(socket_session, "auth_id"))

    def test_valid_node_is_not_disconnected(self):
        org = Organization(name=str(uuid1()))
        col = Collaboration(name=str(uuid1()), organizations=[org])
        node = Node(
            name=str(uuid1()),
            api_key=str(uuid1()),
            organization=org,
            collaboration=col,
        )
        node.save()
        node_id = node.id

        _, disconnect, socket_session = self._connect(identity=node_id)

        disconnect.assert_not_called()
        self.assertEqual(socket_session.auth_id, node_id)
        self.assertEqual(socket_session.type, "node")
