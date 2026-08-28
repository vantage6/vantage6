"""
Regression tests for HQApp.setup_socket_connection().

python-engineio (used by Flask-SocketIO) bundles multiple websocket packets
into a single HTTP long-polling payload, and by default only allows 16
packets per payload (``engineio.payload.Payload.max_decode_packets``). When
many nodes send status messages in a short time window this limit is
exceeded, causing the server to silently fail to decode the remaining
packets in the payload and lose messages (see GH issue #2650).

These tests exercise the real ``setup_socket_connection`` method body (parsed
directly out of ``vantage6.hq.HQApp`` via ``ast``, so the tests run against
the actual production source rather than a re-implementation of it), with
Flask/SocketIO/rabbitmq collaborators replaced by lightweight fakes so the
test does not require a running Flask app, database, or message broker.
"""

import ast
import inspect
import logging

import pytest
from engineio.payload import Payload

from vantage6.hq import HQApp


def _extract_method_source(cls, method_name):
    """Pull the literal source of a method off a class via ast.

    This ensures the test always exercises whatever the method currently
    contains (including future edits), rather than a hand copied version of
    it that could silently drift out of sync with the real implementation.
    """
    src = inspect.getsource(cls)
    tree = ast.parse(src)
    class_node = tree.body[0]
    for item in class_node.body:
        if isinstance(item, ast.FunctionDef) and item.name == method_name:
            return ast.get_source_segment(src, item)
    raise AssertionError(f"{method_name} not found on {cls}")


class _FakeSocketIO:
    """Stand-in for flask_socketio.SocketIO that just records construction."""

    instances = []

    def __init__(self, app, **kwargs):
        self.app = app
        self.kwargs = kwargs
        _FakeSocketIO.instances.append(self)

    def on_namespace(self, namespace):
        self.namespace = namespace


class _FakeNamespace:
    def __init__(self, path, socketio, metrics):
        self.path = path
        self.socketio = socketio
        self.metrics = metrics


class _FakeCtx:
    def __init__(self, config):
        self.config = config


class _FakeHQApp:
    """Minimal stand-in for the parts of HQApp that setup_socket_connection reads."""

    def __init__(self, config, debug=None):
        self.ctx = _FakeCtx(config)
        self.debug = debug or {}
        self.app = object()
        self.metrics = object()


def _call_setup_socket_connection(config):
    """Run the real setup_socket_connection body against a fake self."""
    source = _extract_method_source(HQApp, "setup_socket_connection")
    namespace = {
        "SocketIO": _FakeSocketIO,
        "DefaultSocketNamespace": _FakeNamespace,
        "split_rabbitmq_uri": lambda uri: {"host": "h", "port": 1, "vhost": "v"},
        "log": logging.getLogger("test_socket_connection"),
        "Payload": Payload,
    }
    exec(compile(source, "<setup_socket_connection>", "exec"), namespace)
    method = namespace["setup_socket_connection"]
    fake_self = _FakeHQApp(config)
    return method(fake_self)


@pytest.fixture(autouse=True)
def _reset_payload_limit():
    # engineio.payload.Payload.max_decode_packets is a class attribute shared
    # process-wide, so make sure every test starts from the library default.
    Payload.max_decode_packets = 16
    _FakeSocketIO.instances = []
    yield
    Payload.max_decode_packets = 16


def test_default_max_decode_packets_is_raised_above_library_default():
    _call_setup_socket_connection({})
    assert Payload.max_decode_packets == 128
    assert Payload.max_decode_packets != 16


def test_max_decode_packets_is_configurable():
    _call_setup_socket_connection({"socketio_max_decode_packets": 500})
    assert Payload.max_decode_packets == 500


def test_max_decode_packets_applied_regardless_of_rabbitmq_config():
    _call_setup_socket_connection(
        {"rabbitmq": {"uri": "amqp://user:pass@host:5672/vhost"}}
    )
    assert Payload.max_decode_packets == 128


def test_max_decode_packets_applied_even_when_gevent_uwsgi_mode_fails(monkeypatch):
    """The socketio config is set once up front, so it must still take effect
    when the primary async_mode="gevent_uwsgi" SocketIO() constructor raises
    and the method falls back to the plain SocketIO() constructor."""
    call_count = {"n": 0}

    class _FlakySocketIO(_FakeSocketIO):
        def __init__(self, app, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1 and "async_mode" in kwargs:
                raise RuntimeError("simulated gevent_uwsgi import failure")
            super().__init__(app, **kwargs)

    source = _extract_method_source(HQApp, "setup_socket_connection")
    namespace = {
        "SocketIO": _FlakySocketIO,
        "DefaultSocketNamespace": _FakeNamespace,
        "split_rabbitmq_uri": lambda uri: {"host": "h", "port": 1, "vhost": "v"},
        "log": logging.getLogger("test_socket_connection"),
        "Payload": Payload,
    }
    exec(compile(source, "<setup_socket_connection>", "exec"), namespace)
    method = namespace["setup_socket_connection"]
    fake_self = _FakeHQApp({"socketio_max_decode_packets": 256})

    method(fake_self)

    assert call_count["n"] == 2
    assert Payload.max_decode_packets == 256
