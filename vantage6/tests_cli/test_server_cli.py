import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vantage6.common.globals import APPNAME, InstanceType

from vantage6.cli.common.attach import attach_logs
from vantage6.cli.globals import InfraComponentName
from vantage6.cli.hq.attach import cli_hq_attach
from vantage6.cli.hq.files import cli_hq_files
from vantage6.cli.hq.import_ import cli_hq_import
from vantage6.cli.hq.list import cli_hq_configuration_list
from vantage6.cli.hq.start import cli_hq_start
from vantage6.cli.hq.stop import cli_hq_stop
from vantage6.cli.k8s_config import KubernetesConfig


class CLITestHQ(unittest.TestCase):
    @patch("vantage6.cli.hq.start.select_k8s_config")
    @patch("os.makedirs")
    @patch("vantage6.cli.common.decorator.get_context")
    @patch("vantage6.cli.hq.start.helm_install")
    def test_start(
        self,
        context,
        helm_install,
        os_makedirs,
        ctx_ns,
    ):
        """Start HQ without errors"""

        ctx = MagicMock(
            config={"uri": "sqlite:///file.db", "port": 9999},
            config_file="/config.yaml",
            data_dir=Path("."),
        )
        ctx.config_exists.return_value = True
        ctx.name = "not-running"
        context.return_value = ctx
        ctx_ns.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )

        runner = CliRunner()
        result = runner.invoke(cli_hq_start, ["--name", "not-running"])

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.context.hq.HQContext.available_configurations")
    @patch("vantage6.cli.common.list.find_running_service_names")
    def test_configuration_list(
        self, find_running_service_names, available_configurations
    ):
        """Configuration list without errors."""
        hq_name = "iknl"
        find_running_service_names.return_value = [
            f"{APPNAME}-{hq_name}-system-{InstanceType.HQ.value}"
        ]

        # returns a list of configurations and failed inports
        def side_effect(system_folders):
            config = MagicMock()
            config.name = hq_name
            if not system_folders:
                return [[config], []]
            else:
                return [[config], []]

        available_configurations.side_effect = side_effect

        runner = CliRunner()
        result = runner.invoke(cli_hq_configuration_list)

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.exception)

    @patch("vantage6.cli.common.decorator.get_context")
    def test_files(self, context):
        """Configuration files without errors."""

        ctx = context.return_value = MagicMock(
            log_file="/log_file.log", config_file="/iknl.yaml"
        )
        ctx.get_database_uri.return_value = "sqlite:///test.db"

        runner = CliRunner()
        result = runner.invoke(cli_hq_files, ["--name", "iknl"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.hq.import_.UserClient")
    @patch("vantage6.cli.hq.import_.requests.get")
    @patch("vantage6.cli.hq.import_.click.Path")
    @patch("vantage6.cli.common.decorator.get_context")
    def test_import(self, context, click_path, requests_get, user_client):
        """Import entities without errors."""
        click_path.return_value = MagicMock()
        requests_get.return_value = MagicMock(
            status_code=200, json=lambda: {"version": "1.0.0"}
        )
        user_client.return_value = MagicMock()
        user_client.authenticate.return_value = True

        ctx = MagicMock()
        ctx.name = "some-name"
        context.return_value = ctx

        # Mock the version to match the hq version
        with patch("vantage6.cli.hq.import_.__version__", "1.0.0"):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("some.yaml", "w") as fp:
                    fp.write("""
organizations:
  - name: Test Org
    address1: Test Address
    zipcode: 12345
    country: Test Country
    domain: test.com
    public_key: test-key
    users: []
collaborations: []
""")
                result = runner.invoke(cli_hq_import, ["--name", "iknl", "some.yaml"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

        # check that the import fails when the yaml is invalid
        with patch("vantage6.cli.hq.import_.__version__", "1.0.0"):
            runner = CliRunner()
            with runner.isolated_filesystem():
                with open("some.yaml", "w") as fp:
                    fp.write("invalid")
                result = runner.invoke(cli_hq_import, ["--name", "iknl", "some.yaml"])
                self.assertEqual(result.exit_code, 1)
                self.assertIsNotNone(result.exception)

    @patch("vantage6.cli.common.stop.select_k8s_config")
    @patch("vantage6.cli.common.stop.find_running_service_names")
    @patch("vantage6.cli.common.stop.get_context")
    @patch("vantage6.cli.hq.stop._stop_hq")
    def test_stop(
        self,
        _stop_hq,
        get_context,
        find_running_service_names,
        context_and_namespace,
    ):
        """Stop HQ without errors."""

        instance_name = "iknl"
        hq_name = f"{APPNAME}-{instance_name}-system-{InstanceType.HQ.value}"

        find_running_service_names.return_value = [hq_name]
        get_context.return_value = MagicMock(helm_release_name=hq_name)
        context_and_namespace.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )

        runner = CliRunner()
        result = runner.invoke(cli_hq_stop, ["--name", instance_name])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.hq.attach.attach_logs")
    @patch("vantage6.cli.hq.attach.select_k8s_config")
    def test_attach(self, select_k8s_config, attach_logs):
        """Attach logs to the console without errors."""
        select_k8s_config.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )
        runner = CliRunner()
        result = runner.invoke(cli_hq_attach)

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
        attach_logs.assert_called_once_with(
            name=None,
            instance_type=InstanceType.HQ,
            infra_component=InfraComponentName.HQ,
            system_folders=False,
            k8s_config=KubernetesConfig(
                context="test-context",
                namespace="test-namespace",
            ),
            is_sandbox=False,
            additional_labels="component=vantage6-hq",
        )

    @patch("vantage6.cli.common.utils.subprocess.run")
    @patch("vantage6.cli.common.attach.select_running_service")
    @patch("vantage6.cli.hq.attach.select_k8s_config")
    @patch("vantage6.cli.common.attach.Popen")
    def test_attach_logs(
        self,
        mock_popen,
        select_k8s_config,
        select_running_service,
        subprocess_run,
    ):
        select_k8s_config.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )
        select_running_service.return_value = "vantage6-iknl-system-hq"

        # Mock subprocess.run to return success for helm list command
        subprocess_run.return_value = MagicMock(
            returncode=0,
            stdout='[{"name": "vantage6-iknl-system-hq", "status": "deployed"}]',
        )

        # Mock the Popen instance and its methods
        mock_process = mock_popen.return_value
        mock_process.wait.return_value = None

        # Call the function with a sample label
        attach_logs(
            name=None,
            instance_type=InstanceType.HQ,
            infra_component=InfraComponentName.HQ,
            system_folders=True,
            k8s_config=select_k8s_config.return_value,
            is_sandbox=False,
            additional_labels="test=label",
        )

        # Construct the expected command
        expected_command = [
            "kubectl",
            "--context",
            "test-context",
            "-n",
            "test-namespace",
            "logs",
            "--follow",
            "--selector",
            "release=vantage6-iknl-system-hq,test=label",
            "--all-containers=true",
        ]

        # Verify that Popen was called with the expected command
        mock_popen.assert_called_once_with(expected_command, stdout=None, stderr=None)

        # Verify that wait was called on the process
        mock_process.wait.assert_called_once()
