import unittest

from unittest.mock import MagicMock, patch
from pathlib import Path
from click.testing import CliRunner

from vantage6.cli.globals import APPNAME
from vantage6.cli.server import (
    cli_server_start,
    cli_server_configuration_list,
    cli_server_files,
    cli_server_import,
    cli_server_new,
    cli_server_stop,
    cli_server_attach
)


class ServerCLITest(unittest.TestCase):

    @patch("docker.types.Mount")
    @patch("os.makedirs")
    @patch("vantage6.cli.server.pull_if_newer")
    @patch("vantage6.cli.server.ServerContext")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker.addons.check_docker_running")
    def test_start(self, docker_check, containers, context,
                   pull, os_makedirs, mount):
        """Start server without errors"""

        docker_check.return_value = True

        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-system"
        containers.list.return_value = [container1]
        containers.run.return_value = True

        ctx = MagicMock(
            config={
                'uri': 'sqlite:///file.db',
                'port': 9999
            },
            config_file="/config.yaml",
            data_dir=Path(".")
        )
        ctx.config_exists.return_value = True
        ctx.name = 'not-running'
        context.return_value = ctx

        runner = CliRunner()
        result = runner.invoke(cli_server_start, ["--name", "not-running"])

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.server.ServerContext")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker.addons.check_docker_running")
    def test_configuration_list(self, docker_check, containers, context):
        """Configuration list without errors."""
        docker_check.return_value = True

        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-system"
        containers.list.return_value = [container1]

        config = MagicMock(available_environments=["application"])
        config.name = "iknl"
        context.available_configurations.return_value = ([config], [])

        runner = CliRunner()
        result = runner.invoke(cli_server_configuration_list)

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.exception)

    @patch("vantage6.cli.server.ServerContext")
    def test_files(self, context):
        """Configuration files without errors."""

        ctx = context.return_value = MagicMock(
            log_file="/log_file.log",
            config_file="/iknl.yaml"
        )
        ctx.get_database_uri.return_value = "sqlite:///test.db"

        runner = CliRunner()
        result = runner.invoke(cli_server_files, ["--name", "iknl"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("docker.DockerClient.containers")
    @patch("vantage6.cli.server.print_log_worker")
    @patch("vantage6.cli.server.click.Path")
    @patch("vantage6.common.docker.addons.check_docker_running")
    @patch("vantage6.cli.server.ServerContext")
    def test_import(self, context, docker_check, click_path, log, containers):
        """Import entities without errors."""
        click_path.return_value = MagicMock()

        ctx = MagicMock()
        ctx.name = 'some-name'
        context.return_value = ctx

        runner = CliRunner()
        with runner.isolated_filesystem():
            with open("some.yaml", "w") as fp:
                fp.write("does-not-matter")
            result = runner.invoke(cli_server_import, [
                "--name", "iknl", "some.yaml"
            ])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.server.configuration_wizard")
    @patch("vantage6.cli.server.check_config_write_permissions")
    @patch("vantage6.cli.server.ServerContext")
    def test_new(self, context, permissions, wizard):
        """New configuration without errors."""

        context.config_exists.return_value = False
        permissions.return_value = True
        wizard.return_value = "/some/file.yaml"

        runner = CliRunner()
        result = runner.invoke(cli_server_new, ["--name", "iknl"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.server.ServerContext")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker.addons.check_docker_running")
    def test_stop(self, docker_check, containers, context):
        """Stop server without errors."""

        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-system-server"
        containers.list.return_value = [container1]

        ctx = MagicMock(
            config={
                'rabbitmq_uri': None
            }
        )
        context.return_value = ctx

        runner = CliRunner()
        result = runner.invoke(cli_server_stop, ["--name", "iknl"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.server.time.sleep")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker.addons.check_docker_running")
    def test_attach(self, docker_check, containers, sleep):
        """Attach log to the console without errors."""
        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-system-server"
        containers.list.return_value = [container1]

        sleep.side_effect = KeyboardInterrupt("Boom!")

        runner = CliRunner()
        result = runner.invoke(cli_server_attach, ["--name", "iknl"])

        self.assertIsNone(result.exception)
        self.assertEqual(result.exit_code, 0)
