"""
Tests for authenticating socket connections to HQ.

Nodes send their token in the Authorization header. Browsers cannot set headers on
websocket connections, so the UI sends its token in the Socket.IO auth payload
instead. Both ways must authenticate the client.
"""

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from engineio.payload import Payload

from vantage6.common.globals import SOCKETIO_MAX_DECODE_PACKETS, AuthStatus

from vantage6.hq.model import Node, User

from .test_resource_base import MOCK_PRIVATE_KEY_PEM, TestResourceBase

NAMESPACE = "/tasks"


def _token(keycloak_id: str, client_type: str, exp: int = 9999999999, key=None):
    claims = {
        "sub": keycloak_id,
        "vantage6_client_type": client_type,
        "exp": exp,
        "iat": 0,
    }
    return jwt.encode(claims, key or MOCK_PRIVATE_KEY_PEM, algorithm="RS256")


class TestWebsocketAuth(TestResourceBase):
    def _connect(self, auth=None, headers=None):
        return self.server.socketio.test_client(
            self.server.app, namespace=NAMESPACE, auth=auth, headers=headers
        )

    def _received_event_names(self, client) -> list[str]:
        return [msg["name"] for msg in client.get_received(NAMESPACE)]

    def _create_offline_node(self) -> Node:
        node = self.create_node()
        node.status = AuthStatus.OFFLINE.value
        node.save()
        return node

    def test_node_token_in_auth_payload(self):
        node = self._create_offline_node()

        client = self._connect(auth={"token": _token(node.keycloak_id, "node")})

        self.assertEqual(Node.get(node.id).status, AuthStatus.ONLINE.value)
        # nodes are told to sync after connecting
        self.assertIn("sync", self._received_event_names(client))

    def test_node_token_in_header(self):
        node = self._create_offline_node()

        client = self._connect(headers=self.login_node(node))

        self.assertEqual(Node.get(node.id).status, AuthStatus.ONLINE.value)
        self.assertIn("sync", self._received_event_names(client))

    def test_user_token_in_auth_payload(self):
        user = self.create_user()
        user.status = AuthStatus.OFFLINE.value
        user.save()

        self._connect(auth={"token": _token(user.keycloak_id, "user")})

        self.assertEqual(User.get(user.id).status, AuthStatus.ONLINE.value)

    def test_expired_token_in_auth_payload(self):
        node = self._create_offline_node()

        client = self._connect(auth={"token": _token(node.keycloak_id, "node", exp=1)})

        self.assertIn("expired_token", self._received_event_names(client))
        self.assertEqual(Node.get(node.id).status, AuthStatus.OFFLINE.value)

    def test_token_with_invalid_signature_in_auth_payload(self):
        node = self._create_offline_node()
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_key_pem = other_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        client = self._connect(
            auth={"token": _token(node.keycloak_id, "node", key=other_key_pem)}
        )

        self.assertIn("invalid_token", self._received_event_names(client))
        self.assertEqual(Node.get(node.id).status, AuthStatus.OFFLINE.value)

    def test_no_token(self):
        node = self._create_offline_node()

        client = self._connect()

        self.assertNotIn("sync", self._received_event_names(client))
        self.assertEqual(Node.get(node.id).status, AuthStatus.OFFLINE.value)

    def test_max_decode_packets_raised(self):
        self.assertEqual(Payload.max_decode_packets, SOCKETIO_MAX_DECODE_PACKETS)
