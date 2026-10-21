import unittest
from unittest.mock import Mock, patch

from engineio.payload import Payload

from vantage6.common.globals import SOCKETIO_MAX_DECODE_PACKETS

from vantage6.node import Node


class TestSocketTransport(unittest.TestCase):
    def setUp(self):
        # the packet limit is a class attribute, so reset it to the library default
        self.addCleanup(
            setattr, Payload, "max_decode_packets", Payload.max_decode_packets
        )
        Payload.max_decode_packets = 16

    def _make_node(self, config: dict) -> Node:
        node = Node.__new__(Node)
        node.log = Mock()
        node.config = config
        node.debug = {}
        node.client = Mock()
        node.client.hq_url = "http://hq.example"
        node.client.headers = {"Authorization": "Bearer token"}
        return node

    def _connect(self, config: dict) -> Mock:
        node = self._make_node(config)
        with patch("vantage6.node.SocketIO") as socketio_cls:
            socketio_cls.return_value.connected = True
            node.connect_to_socket()
        return socketio_cls.return_value.connect

    def test_websocket_only_by_default(self):
        connect = self._connect({})
        self.assertEqual(connect.call_args.kwargs["transports"], ["websocket"])

    def test_http_polling_allowed(self):
        connect = self._connect({"allow_http_polling": True})
        self.assertIsNone(connect.call_args.kwargs["transports"])

    def test_max_decode_packets_raised(self):
        self._connect({})
        self.assertEqual(Payload.max_decode_packets, SOCKETIO_MAX_DECODE_PACKETS)
