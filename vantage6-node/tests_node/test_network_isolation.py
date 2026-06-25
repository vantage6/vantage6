from unittest.mock import MagicMock, patch

import pytest
from kubernetes import client as k8s_client

from vantage6.node import Node
from vantage6.node.k8s.network_isolation import (
    _probe_pod_reached_target,
    _resolve_host_ips,
    ip_in_cidr,
    select_probe_target,
    validate_algorithm_isolation,
)

EXAMPLE_COM_IP = "93.184.216.34"
EXAMPLE_ORG_IP = "93.184.216.35"
EXAMPLE_NET_IP = "93.184.216.36"


class TestIpInCidr:
    def test_ip_inside_cidr(self):
        assert ip_in_cidr("203.0.113.10", "203.0.113.0/24") is True

    def test_ip_outside_cidr(self):
        assert ip_in_cidr("203.0.113.10", "10.0.0.0/8") is False

    def test_whole_internet_cidr(self):
        assert ip_in_cidr("203.0.113.10", "0.0.0.0/0") is True


class TestSelectProbeTarget:
    @patch(
        "vantage6.node.k8s.network_isolation._resolve_host_ips",
        side_effect=lambda host: {
            "example.com": [EXAMPLE_COM_IP],
            "example.org": [EXAMPLE_ORG_IP],
            "example.net": [EXAMPLE_NET_IP],
        }[host],
    )
    def test_no_whitelist_returns_first_candidate(self, _mock_resolve):
        target = select_probe_target(None)
        assert target == "https://example.com"

    @patch(
        "vantage6.node.k8s.network_isolation._resolve_host_ips",
        side_effect=lambda host: {
            "example.com": [EXAMPLE_COM_IP],
            "example.org": [EXAMPLE_ORG_IP],
            "example.net": [EXAMPLE_NET_IP],
        }[host],
    )
    def test_empty_whitelist_returns_first_candidate(self, _mock_resolve):
        target = select_probe_target([])
        assert target == "https://example.com"

    @patch(
        "vantage6.node.k8s.network_isolation._resolve_host_ips",
        side_effect=lambda host: {
            "example.com": [EXAMPLE_COM_IP],
            "example.org": [EXAMPLE_ORG_IP],
            "example.net": [EXAMPLE_NET_IP],
        }[host],
    )
    def test_google_whitelist_does_not_affect_target(self, _mock_resolve):
        whitelist = [{"ipBlock": {"cidr": "142.250.0.0/15"}}]
        target = select_probe_target(whitelist)
        assert target == "https://example.com"

    @patch(
        "vantage6.node.k8s.network_isolation._resolve_host_ips",
        side_effect=lambda host: {
            "example.com": [EXAMPLE_COM_IP],
            "example.org": [EXAMPLE_ORG_IP],
            "example.net": [EXAMPLE_NET_IP],
        }[host],
    )
    def test_matching_cidr_skips_candidate(self, _mock_resolve):
        whitelist = [{"ipBlock": {"cidr": f"{EXAMPLE_COM_IP}/32"}}]
        target = select_probe_target(whitelist)
        assert target == "https://example.org"

    @patch(
        "vantage6.node.k8s.network_isolation._resolve_host_ips",
        side_effect=lambda host: {
            "example.com": [EXAMPLE_COM_IP],
            "example.org": [EXAMPLE_ORG_IP],
            "example.net": [EXAMPLE_NET_IP],
        }[host],
    )
    def test_broad_whitelist_returns_none(self, _mock_resolve):
        whitelist = [{"ipBlock": {"cidr": "0.0.0.0/0"}}]
        assert select_probe_target(whitelist) is None


class TestResolveHostIps:
    @patch("vantage6.node.k8s.network_isolation.socket.getaddrinfo")
    def test_returns_unique_ipv4_addresses(self, mock_getaddrinfo):
        mock_getaddrinfo.return_value = [
            (None, None, None, None, ("93.184.216.34", 443)),
            (None, None, None, None, ("93.184.216.34", 443)),
        ]

        assert _resolve_host_ips("example.com") == ["93.184.216.34"]


class TestProbePodReachedTarget:
    def _pod_with_exit_code(self, exit_code: int) -> k8s_client.V1Pod:
        return k8s_client.V1Pod(
            status=k8s_client.V1PodStatus(
                container_statuses=[
                    k8s_client.V1ContainerStatus(
                        name="probe",
                        image="curlimages/curl:latest",
                        image_id="curlimages/curl@sha256:abc",
                        ready=False,
                        restart_count=0,
                        state=k8s_client.V1ContainerState(
                            terminated=k8s_client.V1ContainerStateTerminated(
                                exit_code=exit_code
                            )
                        ),
                    )
                ]
            )
        )

    def test_exit_code_zero_means_not_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(0)) is True

    def test_non_zero_exit_code_means_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(28)) is False


class TestValidateAlgorithmIsolation:
    def test_all_candidates_whitelisted_returns_not_isolated(self):
        whitelist = [{"ipBlock": {"cidr": "0.0.0.0/0"}}]
        with patch(
            "vantage6.node.k8s.network_isolation._resolve_host_ips",
            return_value=[EXAMPLE_COM_IP],
        ):
            isolated, message = validate_algorithm_isolation(
                core_api=MagicMock(),
                task_namespace="vantage6-tasks",
                whitelist_egress=whitelist,
                log=MagicMock(),
            )
        assert isolated is False
        assert "whitelist" in message

    @patch("vantage6.node.k8s.network_isolation._wait_for_probe_pod")
    def test_reachable_target_returns_not_isolated(self, mock_wait):
        mock_wait.return_value = TestProbePodReachedTarget()._pod_with_exit_code(0)
        core_api = MagicMock()

        isolated, message = validate_algorithm_isolation(
            core_api=core_api,
            task_namespace="vantage6-tasks",
            whitelist_egress=None,
            log=MagicMock(),
        )

        assert isolated is False
        assert "example.com" in message
        core_api.delete_namespaced_pod.assert_called_once()

    @patch("vantage6.node.k8s.network_isolation._wait_for_probe_pod")
    def test_blocked_target_returns_isolated(self, mock_wait):
        mock_wait.return_value = TestProbePodReachedTarget()._pod_with_exit_code(28)
        core_api = MagicMock()

        isolated, message = validate_algorithm_isolation(
            core_api=core_api,
            task_namespace="vantage6-tasks",
            whitelist_egress=None,
            log=MagicMock(),
        )

        assert isolated is True
        assert "verified" in message


class TestNodeProductionGating:
    def test_production_true_exits_on_isolation_failure(self):
        ctx = MagicMock()
        ctx.config = {"production": True}

        with patch("vantage6.node.validate_required_env_vars"):
            with patch("vantage6.node.ContainerManager") as mock_cm_cls:
                mock_cm = mock_cm_cls.return_value
                mock_cm.ensure_task_namespace.return_value = True
                mock_cm.validate_algorithm_isolation.return_value = (
                    False,
                    "probe failed",
                )
                with patch(
                    "vantage6.node.exit", side_effect=SystemExit(1)
                ) as mock_exit:
                    with patch.object(
                        Node, "_setup_node_client", return_value=MagicMock()
                    ):
                        with pytest.raises(SystemExit):
                            Node(ctx)
                    mock_exit.assert_called_once_with(1)

    def test_production_false_warns_on_isolation_failure(self, caplog):
        ctx = MagicMock()
        ctx.config = {"production": False, "debug": {}}

        def _connect_socket(self):
            self.socketIO = MagicMock()

        with patch("vantage6.node.validate_required_env_vars"):
            with patch("vantage6.node.ContainerManager") as mock_cm_cls:
                mock_cm = mock_cm_cls.return_value
                mock_cm.ensure_task_namespace.return_value = True
                mock_cm.validate_algorithm_isolation.return_value = (
                    False,
                    "probe failed",
                )
                with patch("vantage6.node.exit") as mock_exit:
                    with patch.object(
                        Node, "_setup_node_client", return_value=MagicMock()
                    ):
                        with patch.object(Node, "authenticate"):
                            with patch.object(Node, "setup_encryption"):
                                with patch.object(
                                    Node, "connect_to_socket", _connect_socket
                                ):
                                    with patch.object(Node, "start_processing_threads"):
                                        with patch("vantage6.node.Thread"):
                                            with caplog.at_level("WARNING"):
                                                Node(ctx)
                    mock_exit.assert_not_called()
        assert "probe failed" in caplog.text
