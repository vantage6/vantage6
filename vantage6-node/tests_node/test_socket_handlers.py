import os
import signal
from unittest.mock import MagicMock, patch

import pytest
from keycloak import KeycloakAuthenticationError

from vantage6.node import Node
from vantage6.node.socket import NodeTaskNamespace


def _namespace() -> NodeTaskNamespace:
    """Create a namespace with its logger and node reference mocked out."""
    namespace = NodeTaskNamespace("/tasks")
    namespace.log = MagicMock()
    namespace.node_worker_ref = MagicMock()
    return namespace


def _node() -> Node:
    """Create a node without running its (heavy) initialization."""
    node = Node.__new__(Node)
    node.log = MagicMock()
    node.client = MagicMock()
    return node


class TestTriggerEvent:
    def test_handler_result_is_returned(self):
        namespace = _namespace()
        namespace.on_pong = lambda: "result"

        assert namespace.trigger_event("pong") == "result"

    def test_failing_handler_is_logged_and_does_not_raise(self):
        namespace = _namespace()
        namespace.on_boom = MagicMock(side_effect=RuntimeError("boom"))

        assert namespace.trigger_event("boom") is None
        namespace.log.exception.assert_called_once()

    def test_unknown_event_is_ignored(self):
        namespace = _namespace()

        assert namespace.trigger_event("event_that_does_not_exist") is None
        namespace.log.exception.assert_not_called()

    def test_disconnect_handler_without_reason_is_still_called(self):
        # python-socketio retries the disconnect event without its `reason` argument
        # when the handler does not accept one. Guarding the dispatch should not
        # interfere with that fallback.
        namespace = _namespace()
        calls = []
        namespace.on_disconnect = lambda: calls.append("called")

        namespace.trigger_event("disconnect", "ping timeout")

        assert calls == ["called"]
        namespace.log.exception.assert_not_called()


class TestDeleteDataframe:
    @patch("vantage6.node.socket.SessionFileManager")
    def test_incomplete_instruction_is_ignored(self, mock_session_file_manager):
        namespace = _namespace()
        namespace.emit = MagicMock()

        namespace.on_delete_dataframe({"session_id": 1})

        mock_session_file_manager.assert_not_called()
        namespace.emit.assert_not_called()
        namespace.log.error.assert_called_once()

    @patch("vantage6.node.socket.SessionFileManager")
    def test_dataframe_is_deleted_and_acknowledged(self, mock_session_file_manager):
        namespace = _namespace()
        namespace.emit = MagicMock()

        namespace.on_delete_dataframe({"session_id": 1, "df_name": "df"})

        mock_session_file_manager.return_value.delete_dataframe_file.assert_called_once_with(
            "df"
        )
        event, data = namespace.emit.call_args[0]
        assert event == "dataframe_deleted"
        assert data["df_name"] == "df"
        assert data["session_id"] == 1


class TestKillContainers:
    def test_status_change_is_emitted_for_each_killed_run(self):
        namespace = _namespace()
        namespace.emit = MagicMock()
        namespace.node_worker_ref.kill_containers.return_value = [
            MagicMock(run_id=1, task_id=10, parent_id=None),
            MagicMock(run_id=2, task_id=11, parent_id=10),
        ]

        namespace.on_kill_containers({"collaboration_id": 1})

        assert namespace.emit.call_count == 2
        assert [call[0][1]["run_id"] for call in namespace.emit.call_args_list] == [
            1,
            2,
        ]

    def test_failing_kill_is_reported_via_trigger_event(self):
        namespace = _namespace()
        namespace.node_worker_ref.kill_containers.side_effect = RuntimeError("boom")

        namespace.trigger_event("kill_containers", {"collaboration_id": 1})

        namespace.log.exception.assert_called_once()


class TestFatal:
    @patch("vantage6.node.os.kill")
    def test_node_is_terminated(self, mock_kill):
        # sys.exit() would only end the thread that hit the fatal error, so the node
        # signals itself instead. It is Kubernetes that restarts the node afterwards.
        node = _node()

        with pytest.raises(SystemExit):
            node._fatal("the sky is falling")

        mock_kill.assert_called_once_with(os.getpid(), signal.SIGTERM)
        node.log.critical.assert_called_once_with("the sky is falling")

    @patch("vantage6.node.os.kill")
    def test_message_placeholders_are_filled_in_by_the_logger(self, _mock_kill):
        node = _node()

        with pytest.raises(SystemExit):
            node._fatal("cannot reach %s", "hq")

        node.log.critical.assert_called_once_with("cannot reach %s", "hq")

    def test_node_really_stops_when_the_signal_is_not_fatal(self):
        # if a SIGTERM handler is ever installed, os.kill() no longer ends the process
        # by itself. The node should still not continue past a fatal error.
        node = _node()

        with patch("vantage6.node.os.kill"), pytest.raises(SystemExit):
            node._fatal("the sky is falling")


class TestProxyServerWorker:
    @patch("vantage6.node.os.kill")
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_proxy_host_shuts_the_node_down(self, _mock_kill):
        # this runs in the node's proxy thread, where sys.exit() would only have ended
        # that thread and left the node running without a proxy server
        node = _node()

        with pytest.raises(SystemExit):
            node._Node__proxy_server_worker()

        assert "V6_PROXY_HOST" in node.log.critical.call_args[0][0]


class TestAuthenticate:
    @patch("vantage6.node.os.kill")
    @patch("vantage6.node.time.sleep")
    def test_failure_shuts_the_node_down(self, _mock_sleep, _mock_kill):
        node = _node()
        node.client.authenticate.side_effect = KeycloakAuthenticationError(
            "wrong API key"
        )

        with pytest.raises(SystemExit):
            node.authenticate()

        node.client.auto_renew_token.assert_not_called()


class TestConnectToSocket:
    @patch("vantage6.node.os.kill")
    @patch("vantage6.node.time.sleep")
    @patch("vantage6.node.SocketIO")
    def test_timeout_shuts_the_node_down(self, mock_socketio, _mock_sleep, _mock_kill):
        node = _node()
        node.debug = {}
        mock_socketio.return_value.connected = False

        with pytest.raises(SystemExit):
            node.connect_to_socket()
