from unittest.mock import MagicMock, patch

import pytest
from kubernetes import client as k8s_client

from vantage6.common.globals import NodePolicy

from vantage6.node import Node
from vantage6.node.globals import ISOLATION_PROBE_CANDIDATES
from vantage6.node.k8s.network_isolation import (
    _probe_pod_reached_target,
    validate_algorithm_isolation,
)


class TestProbePodReachedTarget:
    def _pod_with_exit_code(self, *exit_codes: int) -> k8s_client.V1Pod:
        return k8s_client.V1Pod(
            status=k8s_client.V1PodStatus(
                container_statuses=[
                    k8s_client.V1ContainerStatus(
                        name=f"probe-{idx}",
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
                    for idx, exit_code in enumerate(exit_codes)
                ]
            )
        )

    def test_exit_code_zero_means_not_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(0)) is True

    def test_non_zero_exit_code_means_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(28)) is False

    def test_one_reached_candidate_means_not_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(28, 0, 6)) is True

    def test_all_blocked_candidates_mean_isolated(self):
        assert _probe_pod_reached_target(self._pod_with_exit_code(28, 28, 6)) is False


class TestValidateAlgorithmIsolation:
    @patch("vantage6.node.k8s.network_isolation._wait_for_probe_pod")
    def test_reachable_target_returns_not_isolated(self, mock_wait):
        mock_wait.return_value = TestProbePodReachedTarget()._pod_with_exit_code(0)
        core_api = MagicMock()

        isolated, message = validate_algorithm_isolation(
            core_api=core_api,
            task_namespace="vantage6-tasks",
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
            log=MagicMock(),
        )

        assert isolated is True
        assert "verified" in message

    @patch("vantage6.node.k8s.network_isolation._wait_for_probe_pod")
    def test_probe_pod_is_shell_free_and_configurable(self, mock_wait):
        mock_wait.return_value = TestProbePodReachedTarget()._pod_with_exit_code(28)
        core_api = MagicMock()
        labels = {"v6-pod-type": "algorithm", "role": "central_compute"}

        validate_algorithm_isolation(
            core_api=core_api,
            task_namespace="tenant",
            log=MagicMock(),
            labels=labels,
            image="registry.local/curl:1",
        )

        pod = core_api.create_namespaced_pod.call_args.kwargs["body"]
        assert pod.metadata.labels == labels
        assert len(pod.spec.containers) == len(ISOLATION_PROBE_CANDIDATES)
        for container, url in zip(pod.spec.containers, ISOLATION_PROBE_CANDIDATES):
            assert container.image == "registry.local/curl:1"
            assert container.command == ["curl"]
            assert container.args[-1] == url


_ALGORITHM_POLICY = {NodePolicy.ALLOWED_ALGORITHMS.value: ["^some/image$"]}


class TestNodeProductionGating:
    def test_production_true_exits_on_isolation_failure(self):
        ctx = MagicMock()
        ctx.config = {"production": True, "policies": _ALGORITHM_POLICY}

        with (
            patch("vantage6.node.validate_required_env_vars"),
            patch("vantage6.node.ContainerManager") as mock_cm_cls,
        ):
            mock_cm = mock_cm_cls.return_value
            mock_cm.can_create_algorithm_pods.return_value = True
            mock_cm.validate_algorithm_isolation.return_value = (
                False,
                "probe failed",
            )
            with patch(
                "vantage6.node.sys.exit", side_effect=SystemExit(1)
            ) as mock_exit:
                with (
                    patch.object(Node, "_setup_node_client", return_value=MagicMock()),
                    pytest.raises(SystemExit),
                ):
                    Node(ctx)
                mock_exit.assert_called_once_with(1)

    def test_production_false_warns_on_isolation_failure(self, caplog):
        ctx = MagicMock()
        ctx.config = {
            "production": False,
            "debug": {},
            "policies": _ALGORITHM_POLICY,
        }

        def _connect_socket(self):
            self.socketIO = MagicMock()

        with (
            patch("vantage6.node.validate_required_env_vars"),
            patch("vantage6.node.ContainerManager") as mock_cm_cls,
        ):
            mock_cm = mock_cm_cls.return_value
            mock_cm.can_create_algorithm_pods.return_value = True
            mock_cm.validate_algorithm_isolation.return_value = (
                False,
                "probe failed",
            )
            with patch("vantage6.node.sys.exit") as mock_exit:
                with (
                    patch.object(Node, "_setup_node_client", return_value=MagicMock()),
                    patch.object(Node, "authenticate"),
                    patch.object(Node, "setup_encryption"),
                    patch.object(Node, "connect_to_socket", _connect_socket),
                    patch.object(Node, "start_processing_threads"),
                    patch("vantage6.node.Thread"),
                    caplog.at_level("WARNING"),
                ):
                    Node(ctx)
                mock_exit.assert_not_called()
        assert "probe failed" in caplog.text

    def test_verify_disabled_skips_probe_in_production(self, caplog):
        ctx = MagicMock()
        ctx.config = {
            "production": True,
            "debug": {},
            "policies": _ALGORITHM_POLICY,
            "network_isolation": {"verify": False},
        }

        def _connect_socket(self):
            self.socketIO = MagicMock()

        with (
            patch("vantage6.node.validate_required_env_vars"),
            patch("vantage6.node.ContainerManager") as mock_cm_cls,
        ):
            mock_cm = mock_cm_cls.return_value
            mock_cm.can_create_algorithm_pods.return_value = True
            with patch("vantage6.node.sys.exit") as mock_exit:
                with (
                    patch.object(Node, "_setup_node_client", return_value=MagicMock()),
                    patch.object(Node, "authenticate"),
                    patch.object(Node, "setup_encryption"),
                    patch.object(Node, "connect_to_socket", _connect_socket),
                    patch.object(Node, "start_processing_threads"),
                    patch("vantage6.node.Thread"),
                    caplog.at_level("WARNING"),
                ):
                    Node(ctx)
                mock_exit.assert_not_called()
            mock_cm.validate_algorithm_isolation.assert_not_called()
        assert "NOT verified" in caplog.text

    def test_exits_when_algorithm_pods_cannot_be_created(self):
        ctx = MagicMock()
        ctx.config = {"production": True, "policies": _ALGORITHM_POLICY}

        with (
            patch("vantage6.node.validate_required_env_vars"),
            patch("vantage6.node.ContainerManager") as mock_cm_cls,
        ):
            mock_cm_cls.return_value.can_create_algorithm_pods.return_value = False
            with patch(
                "vantage6.node.sys.exit", side_effect=SystemExit(1)
            ) as mock_exit:
                with (
                    patch.object(Node, "_setup_node_client", return_value=MagicMock()),
                    pytest.raises(SystemExit),
                ):
                    Node(ctx)
                mock_exit.assert_called_once_with(1)
