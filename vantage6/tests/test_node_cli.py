import unittest
import logging
import contextlib

from unittest.mock import MagicMock, patch
from pathlib import Path
from io import BytesIO, StringIO
from click.testing import CliRunner
from docker.errors import APIError

from vantage6.cli.globals import APPNAME
from vantage6.common import STRING_ENCODING
from vantage6.common.docker_addons import check_docker_running
from vantage6.cli.node import (
    cli_node_list,
    cli_node_new_configuration,
    cli_node_files,
    cli_node_start,
    cli_node_stop,
    cli_node_attach,
    cli_node_create_private_key,
    cli_node_clean,
    print_log_worker,
    create_client_and_authenticate,
)


class NodeCLITest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        logging.getLogger("docker.utils.config").setLevel(logging.WARNING)
        return super().setUpClass()

    @patch("docker.DockerClient.ping")
    def test_list_docker_not_running(self, docker_ping):
        """An error is printed when docker is not running"""
        docker_ping.side_effect = Exception('Boom!')

        runner = CliRunner()
        result = runner.invoke(cli_node_list, [])

        # check exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.context.NodeContext.available_configurations")
    @patch("docker.DockerClient.ping")
    @patch("docker.DockerClient.containers")
    def test_list(self, containers, docker_ping, available_configurations):
        """A container list and their current status."""
        # https://docs.python.org/3/library/unittest.mock.html#mock-names-and-the-name-attribute

        # mock that docker-deamon is running
        docker_ping.return_value = True

        # docker deamon returns a list of running node-containers
        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-user"
        containers.list.return_value = [container1]

        # returns a list of configurations and failed inports
        def side_effect(system_folders):
            config = MagicMock(available_environments=["Application"])
            config.name = "iknl"
            if not system_folders:
                return [[config], []]
            else:
                return [[config], []]

        available_configurations.side_effect = side_effect

        # invoke CLI method
        runner = CliRunner()
        result = runner.invoke(cli_node_list, [])

        # validate exit code
        self.assertEqual(result.exit_code, 0)

        # check printed lines
        self.assertEqual(
            result.output,
            "\nName                     Environments                    Status          System/User\n"
            "-------------------------------------------------------------------------------------\n"
            "iknl                     ['Application']                 Offline          System \n"
            "iknl                     ['Application']                 Online           User   \n"
            "-------------------------------------------------------------------------------------\n"
        )

    @patch("vantage6.cli.node.configuration_wizard")
    @patch("vantage6.cli.node.check_config_write_permissions")
    @patch("vantage6.cli.node.NodeContext")
    def test_new_config(self, context, permissions, wizard):
        """No error produced when creating new configuration."""
        context.config_exists.return_value = False
        permissions.return_value = True
        wizard.return_value = "/some/file/path"

        runner = CliRunner()
        result = runner.invoke(cli_node_new_configuration, [
            "--name", "some-name",
            "--environment", "application"
        ])

        # check that info message is produced
        self.assertEqual(result.output[:6], "[info]")

        # check OK exit code
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.configuration_wizard")
    def test_new_config_replace_whitespace_in_name(self, _):
        """Whitespaces are replaced in the name."""

        runner = CliRunner()
        result = runner.invoke(cli_node_new_configuration, [
            "--name", "some name",
            "--environment", "application"
        ])

        self.assertEqual(
            result.output[:60],
            "[info]  - Replaced spaces from configuration name: some-name"
        )

    @patch("vantage6.cli.node.NodeContext")
    def test_new_config_already_exists(self, context):
        """No duplicate configurations are allowed."""

        context.config_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(cli_node_new_configuration, [
            "--name", "some-name",
            "--environment", "application"
        ])

        # check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.check_config_write_permissions")
    @patch("vantage6.cli.node.NodeContext")
    def test_new_write_permissions(self, context, permissions):
        """User needs write permissions."""

        context.config_exists.return_value = False
        permissions.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_new_configuration, [
            "--name", "some-name",
            "--environment", "application"
        ])

        # check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.NodeContext")
    @patch("vantage6.cli.node.select_configuration_questionaire")
    def test_files(self, select_config, context):
        """No errors produced when retrieving filepaths."""

        context.config_exists.return_value = True
        context.return_value = MagicMock(
            config_file="/file.yaml",
            log_file="/log.log",
            data_dir="/dir"
        )
        context.return_value.databases.items.return_value = \
            [["label", "/file.db"]]
        select_config.return_value = ["iknl", "application"]

        runner = CliRunner()
        result = runner.invoke(cli_node_files, [])

        # we check that no warnings have been produced
        self.assertEqual(result.output[:6], "[info]")

        # check status code is OK
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.NodeContext")
    def test_files_non_existing_config(self, context):
        """An error is produced when a non existing config is used."""

        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_files, ['--name', 'non-existing'])

        # Check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check for non zero exit-code
        self.assertNotEqual(result.exit_code, 0)

    @patch("docker.DockerClient.volumes")
    @patch("vantage6.cli.node.pull_if_newer")
    @patch("vantage6.cli.node.NodeContext")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker_addons.check_docker_running")
    def test_start(self, check_docker, client, context, pull, volumes):

        # client.containers = MagicMock(name="docker.DockerClient.containers")
        client.list.return_value = []
        volume = MagicMock()
        volume.name = "data-vol-name"
        volumes.create.return_value = volume
        check_docker.return_value = True
        context.config_exists.return_value = True

        ctx = MagicMock(
            data_dir=Path("data"),
            log_dir=Path("logs"),
            config_dir=Path("configs"),
            databases={"default": "data.csv"}
        )
        ctx.get_data_file.return_value = "data.csv"
        ctx.name = 'some-name'
        context.return_value = ctx

        runner = CliRunner()

        with runner.isolated_filesystem():
            result = runner.invoke(cli_node_start, ['--name', 'some-name'])

        self.assertEqual(result.exit_code, 0)

    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker_addons.check_docker_running")
    def test_stop(self, check_docker, containers):

        check_docker.return_value = True

        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-user"
        containers.list.return_value = [container1]

        runner = CliRunner()

        result = runner.invoke(cli_node_stop, ['--name', 'iknl'])

        self.assertEqual(
            result.output,
            "[info]  - Stopped the vantage6-iknl-user Node.\n"
        )

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.time")
    @patch("vantage6.cli.node.print_log_worker")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.common.docker_addons.check_docker_running")
    def test_attach(self, check_docker, containers, log_worker, time_):
        """Attach docker logs without errors."""
        check_docker.return_value = True

        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-user"
        containers.list.return_value = [container1]

        log_worker.return_value = ""
        time_.sleep.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(cli_node_attach, ['--name', 'iknl'])

        self.assertEqual(
            result.output,
            "[info]  - Closing log file. Keyboard Interrupt.\n"
        )
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.q")
    @patch("docker.DockerClient.volumes")
    @patch("vantage6.common.docker_addons.check_docker_running")
    def test_clean(self, check_docker, volumes, q):
        """Clean Docker volumes without errors."""

        volume1 = MagicMock()
        volume1.name = "some-name-tmpvol"
        volumes.list.return_value = [volume1]

        question = MagicMock(name="pop-the-question")
        question.ask.return_value = True
        q.confirm.return_value = question

        runner = CliRunner()
        result = runner.invoke(cli_node_clean)

        # check exit code
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.create_client_and_authenticate")
    @patch("vantage6.cli.node.NodeContext")
    def test_create_private_key(self, context, client):
        context.config_exists.return_value = True
        context.return_value.type_data_folder.return_value = Path(".")
        client.return_value = MagicMock(
            whoami=MagicMock(organization_name="Test")
        )
        # client.whoami.organization_name = "Test"
        runner = CliRunner()

        result = runner.invoke(cli_node_create_private_key,
                               ["--name", "application"])

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.RSACryptor")
    @patch("vantage6.cli.node.create_client_and_authenticate")
    @patch("vantage6.cli.node.NodeContext")
    def test_create_private_key_overwite(self, context, client, cryptor):
        context.config_exists.return_value = True
        context.return_value.type_data_folder.return_value = Path(".")
        client.return_value = MagicMock(
            whoami=MagicMock(organization_name="Test")
        )
        cryptor.create_public_key_bytes.return_value = b''
        # client.whoami.organization_name = "Test"

        runner = CliRunner()

        # overwrite
        with runner.isolated_filesystem():
            with open("privkey_iknl.pem", "w") as f:
                f.write("does-not-matter")

            result = runner.invoke(cli_node_create_private_key, [
                "--name",
                "application",
                "--overwrite",
                "--organization-name",
                "iknl"
            ])
        self.assertEqual(result.exit_code, 0)

        # do not overwrite
        with runner.isolated_filesystem():
            with open("privkey_iknl.pem", "w") as f:
                f.write("does-not-matter")

            result = runner.invoke(cli_node_create_private_key, [
                "--name",
                "application",
                "--organization-name",
                "iknl"
            ])

            # print(result.output)

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.NodeContext")
    def test_create_private_key_config_not_found(self, context):
        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_create_private_key,
                               ["--name", "application"])

        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.q")
    @patch("docker.DockerClient.volumes")
    @patch("vantage6.common.docker_addons.check_docker_running")
    def test_clean_docker_error(self, check_docker, volumes, q):

        volume1 = MagicMock()
        volume1.name = "some-name-tmpvol"
        volume1.remove.side_effect = APIError("Testing")
        volumes.list.return_value = [volume1]
        question = MagicMock(name="pop-the-question")
        question.ask.return_value = True
        q.confirm.return_value = question

        runner = CliRunner()
        result = runner.invoke(cli_node_clean)

        # check exit code
        self.assertEqual(result.exit_code, 1)

    def test_print_log_worker(self):
        stream = BytesIO("Hello!".encode(STRING_ENCODING))
        temp_stdout = StringIO()
        with contextlib.redirect_stdout(temp_stdout):
            print_log_worker(stream)
        output = temp_stdout.getvalue().strip()
        self.assertEqual(output, "Hello!")

    @patch("vantage6.cli.node.info")
    @patch("vantage6.cli.node.debug")
    @patch("vantage6.cli.node.error")
    @patch("vantage6.cli.node.Client")
    @patch("vantage6.cli.node.q")
    def test_client(self, q, client, error, debug, info):

        ctx = MagicMock(
            config={
                "server_url": "localhost",
                "port": 5000,
                "api_path": ""
            }
        )

        # should not trigger an exception
        try:
            create_client_and_authenticate(ctx)
        except Exception:
            self.fail("Raised an exception!")

        # client raises exception
        client.side_effect = Exception("Boom!")
        with self.assertRaises(Exception):
            create_client_and_authenticate(ctx)

    # TODO this function has been moved to the common package. A test should
    # be added there instead of here
    # @patch("vantage6.cli.node.error")
    # def test_check_docker(self, error):
    #     docker = MagicMock()
    #     try:
    #         check_docker_running()
    #     except Exception:
    #         self.fail("Exception raised!")

    #     docker.ping.side_effect = Exception("Boom!")
    #     with self.assertRaises(SystemExit):
    #         check_docker_running()
