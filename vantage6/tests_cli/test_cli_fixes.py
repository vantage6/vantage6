import unittest
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vantage6.common.globals import InstanceType

from vantage6.cli.common.start import helm_install
from vantage6.cli.common.stop import execute_stop
from vantage6.cli.globals import ChartName, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.node.version import cli_node_version

K8S_CONFIG = KubernetesConfig(context="ctx", namespace="ns")


class TestExecuteStop(unittest.TestCase):
    @patch("vantage6.cli.common.stop.select_k8s_config", return_value=K8S_CONFIG)
    @patch("vantage6.cli.common.stop.find_running_service_names")
    def test_stop_all_passes_the_same_arguments_as_a_single_stop(self, running, _):
        running.return_value = ["vantage6-a-user-node", "vantage6-b-user-node"]
        stop_function = MagicMock()

        execute_stop(
            stop_function=stop_function,
            instance_type=InstanceType.NODE,
            infra_component=InfraComponentName.NODE,
            stop_all=True,
            to_stop=None,
            namespace="ns",
            context="ctx",
            system_folders=False,
            stop_function_args={"system_folders": False, "is_sandbox": False},
        )

        self.assertEqual(stop_function.call_count, 2)
        stop_function.assert_any_call(
            "vantage6-a-user-node",
            K8S_CONFIG,
            system_folders=False,
            is_sandbox=False,
        )


class TestHelmInstall(unittest.TestCase):
    @patch("vantage6.cli.common.start.subprocess.run")
    def test_without_k8s_config(self, run):
        helm_install("rel", ChartName.NODE, chart_version="1.0.0")
        command = run.call_args.args[0]
        self.assertNotIn("--kube-context", command)
        self.assertNotIn("--namespace", command)


class TestNodeVersion(unittest.TestCase):
    @patch("vantage6.cli.node.version.stream", return_value="5.1.0\n")
    @patch("vantage6.cli.node.version.get_core_api_with_ssl_handling")
    @patch("vantage6.cli.node.version.get_and_select_ctx")
    @patch("vantage6.cli.node.version.select_k8s_config", return_value=K8S_CONFIG)
    def test_version_uses_selected_context(self, _, get_ctx, get_core, stream):
        get_ctx.return_value = MagicMock(helm_release_name="vantage6-a-user-node")
        pod = MagicMock()
        pod.metadata.name = "node-pod"
        pod.status.conditions = []
        get_core.return_value.list_namespaced_pod.return_value.items = [pod]

        result = CliRunner().invoke(cli_node_version, ["--name", "a"])

        self.assertEqual(result.exit_code, 0, result.output)
        get_ctx.assert_called_once_with(
            InstanceType.NODE, "a", False, "ctx", "ns", False
        )
        get_core.assert_called_with(context="ctx")
        self.assertEqual(stream.call_args.args[2], "ns")
        self.assertIn("5.1.0", result.output)


if __name__ == "__main__":
    unittest.main()
