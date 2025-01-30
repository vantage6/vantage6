import unittest
import logging
import os
import contextlib

from unittest.mock import MagicMock, patch
from pathlib import Path
from io import BytesIO, StringIO
from click.testing import CliRunner
from docker.errors import APIError

from vantage6.common.globals import Ports
from vantage6.cli.globals import APPNAME
from vantage6.common import STRING_ENCODING
from vantage6.cli.common.utils import print_log_worker
from vantage6.cli.node.list import cli_node_list
from vantage6.cli.node.new import cli_node_new_configuration
from vantage6.cli.node.files import cli_node_files
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.restart import cli_node_restart
from vantage6.cli.node.stop import cli_node_stop
from vantage6.cli.node.attach import cli_node_attach
from vantage6.cli.node.create_private_key import cli_node_create_private_key
from vantage6.cli.node.clean import cli_node_clean
from vantage6.cli.node.common import create_client_and_authenticate


class NodeCLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.getLogger("docker.utils.config").setLevel(logging.WARNING)
        return super().setUpClass()

    @patch("docker.DockerClient.ping")
    def test_list_docker_not_running(self, docker_ping):
        """An error is printed when docker is not running"""
        docker_ping.side_effect = Exception("Boom!")

        runner = CliRunner()
        result = runner.invoke(cli_node_list, [])

        # check exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.context.node.NodeContext.available_configurations")
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
            config = MagicMock()
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
            "\nName                     Status          System/User\n"
            "-----------------------------------------------------\n"
            "iknl                     Not running     System \n"
            "iknl                     Running         User   \n"
            "-----------------------------------------------------\n",
        )

    @patch("vantage6.cli.node.new.configuration_wizard")
    @patch("vantage6.cli.node.new.ensure_config_dir_writable")
    @patch("vantage6.cli.node.common.NodeContext")
    def test_new_config(self, context, permissions, wizard):
        """No error produced when creating new configuration."""
        context.config_exists.return_value = False
        permissions.return_value = True
        wizard.return_value = "/some/file/path"

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some-name",
            ],
        )

        # check that info message is produced
        self.assertEqual(result.output[:7], "[info ]")

        # check OK exit code
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.new.configuration_wizard")
    def test_new_config_replace_whitespace_in_name(self, _):
        """Whitespaces are replaced in the name."""

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some name",
            ],
        )

        self.assertEqual(
            result.output[:60],
            "[info ] - Replaced spaces from configuration name: some-name",
        )

    @patch("vantage6.cli.node.new.NodeContext")
    def test_new_config_already_exists(self, context):
        """No duplicate configurations are allowed."""

        context.config_exists.return_value = True

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some-name",
            ],
        )

        # check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.new.ensure_config_dir_writable")
    @patch("vantage6.cli.node.common.NodeContext")
    def test_new_write_permissions(self, context, permissions):
        """User needs write permissions."""

        context.config_exists.return_value = False
        permissions.return_value = False

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some-name",
            ],
        )

        # check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.common.NodeContext")
    @patch("vantage6.cli.node.files.NodeContext")
    @patch("vantage6.cli.node.common.select_configuration_questionaire")
    def test_files(self, select_config, context, common_context):
        """No errors produced when retrieving filepaths."""

        common_context.config_exists.return_value = True
        context.return_value = MagicMock(
            config_file="/file.yaml", log_file="/log.log", data_dir="/dir"
        )
        context.return_value.databases.items.return_value = [["label", "/file.db"]]
        select_config.return_value = "iknl"

        runner = CliRunner()
        result = runner.invoke(cli_node_files, [])

        # we check that no warnings have been produced
        self.assertEqual(result.output[:7], "[info ]")

        # check status code is OK
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.common.NodeContext")
    def test_files_non_existing_config(self, context):
        """An error is produced when a non existing config is used."""

        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_files, ["--name", "non-existing"])

        # Check that error is produced
        self.assertEqual(result.output[:7], "[error]")

        # check for non zero exit-code
        self.assertNotEqual(result.exit_code, 0)

    @patch("docker.DockerClient.volumes")
    @patch("vantage6.cli.node.start.pull_infra_image")
    @patch("vantage6.cli.common.decorator.get_context")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.cli.node.start.check_docker_running", return_value=True)
    def test_start(self, check_docker, client, context, pull, volumes):
        # client.containers = MagicMock(name="docker.DockerClient.containers")
        client.list.return_value = []
        volume = MagicMock()
        volume.name = "data-vol-name"
        volumes.create.return_value = volume
        context.config_exists.return_value = True

        ctx = MagicMock(
            data_dir=Path("data"),
            log_dir=Path("logs"),
            config_dir=Path("configs"),
            databases=[{"label": "some_label", "uri": "data.csv", "type": "csv"}],
        )

        # cli_node_start() tests for truth value of a set-like object derived
        # from ctx.config.get('node_extra_env', {}). Default MagicMock() will
        # evaluate to True, empty dict to False. False signifies no overwritten
        # env vars, hence no error.
        def config_get_side_effect(key, default=None):
            if key == "node_extra_env":
                return {}
            return MagicMock()

        ctx.config.get.side_effect = config_get_side_effect
        ctx.get_data_file.return_value = "data.csv"
        ctx.name = "some-name"
        context.return_value = ctx

        runner = CliRunner()

        # Should fail when starting node with non-existing database CSV file
        with runner.isolated_filesystem():
            result = runner.invoke(cli_node_start, ["--name", "some-name"])
        self.assertEqual(result.exit_code, 1)

        # now do it with a SQL database which doesn't have to be an existing file
        ctx.databases = [{"label": "some_label", "uri": "data.db", "type": "sql"}]
        with runner.isolated_filesystem():
            result = runner.invoke(cli_node_start, ["--name", "some-name"])
        self.assertEqual(result.exit_code, 0)

    def _setup_stop_test(self, containers):
        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-user"
        containers.list.return_value = [container1]

    @patch("docker.DockerClient.containers")
    @patch("vantage6.cli.node.stop.check_docker_running", return_value=True)
    @patch("vantage6.cli.node.stop.NodeContext")
    @patch("vantage6.cli.node.stop.delete_volume_if_exists")
    def test_stop(self, delete_volume, node_context, check_docker, containers):
        self._setup_stop_test(containers)

        runner = CliRunner()

        result = runner.invoke(cli_node_stop, ["--name", "iknl"])

        self.assertEqual(
            result.output, "[info ] - Stopped the vantage6-iknl-user Node.\n"
        )

        self.assertEqual(result.exit_code, 0)

    @patch("docker.DockerClient.containers")
    @patch("vantage6.cli.node.stop.check_docker_running", return_value=True)
    @patch("vantage6.cli.node.stop.NodeContext")
    @patch("vantage6.cli.node.stop.delete_volume_if_exists")
    @patch("vantage6.cli.node.restart.subprocess.run")
    def test_restart(
        self, subprocess_run, delete_volume, node_context, check_docker, containers
    ):
        """Restart a node without errors."""
        self._setup_stop_test(containers)
        # The subprocess.run() function is called with the command to start the node.
        # Unfortunately it is hard to test this, so we just return a successful run
        subprocess_run.return_value = MagicMock(returncode=0)
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli_node_restart, ["--name", "iknl"])
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.attach.time")
    @patch("vantage6.cli.node.attach.print_log_worker")
    @patch("docker.DockerClient.containers")
    @patch("vantage6.cli.node.attach.check_docker_running", return_value=True)
    def test_attach(self, check_docker, containers, log_worker, time_):
        """Attach docker logs without errors."""
        container1 = MagicMock()
        container1.name = f"{APPNAME}-iknl-user"
        containers.list.return_value = [container1]

        log_worker.return_value = ""
        time_.sleep.side_effect = KeyboardInterrupt()

        runner = CliRunner()
        result = runner.invoke(cli_node_attach, ["--name", "iknl"])

        self.assertEqual(
            result.output,
            "[info ] - Closing log file. Keyboard Interrupt.\n"
            "[info ] - Note that your node is still running! Shut it down "
            "with 'v6 node stop'\n",
        )
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.clean.q")
    @patch("docker.DockerClient.volumes")
    @patch("vantage6.cli.node.clean.check_docker_running", return_value=True)
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

    @patch("vantage6.cli.node.create_private_key.create_client_and_authenticate")
    @patch("vantage6.cli.node.common.NodeContext")
    @patch("vantage6.cli.node.create_private_key.NodeContext")
    def test_create_private_key(self, context, common_context, client):
        common_context.config_exists.return_value = True
        context.return_value.type_data_folder.return_value = Path(".")
        client.return_value = MagicMock(whoami=MagicMock(organization_name="Test"))
        # client.whoami.organization_name = "Test"
        runner = CliRunner()

        result = runner.invoke(cli_node_create_private_key, ["--name", "application"])

        self.assertEqual(result.exit_code, 0)

        # remove the private key file again
        os.remove("privkey_Test.pem")

    @patch("vantage6.cli.node.create_private_key.RSACryptor")
    @patch("vantage6.cli.node.create_private_key.create_client_and_authenticate")
    @patch("vantage6.cli.node.common.NodeContext")
    @patch("vantage6.cli.node.create_private_key.NodeContext")
    def test_create_private_key_overwite(
        self, context, common_context, client, cryptor
    ):
        common_context.config_exists.return_value = True
        context.return_value.type_data_folder.return_value = Path(".")
        client.return_value = MagicMock(whoami=MagicMock(organization_name="Test"))
        cryptor.create_public_key_bytes.return_value = b""
        # client.whoami.organization_name = "Test"

        runner = CliRunner()

        # overwrite
        with runner.isolated_filesystem():
            with open("privkey_iknl.pem", "w") as f:
                f.write("does-not-matter")

            result = runner.invoke(
                cli_node_create_private_key,
                ["--name", "application", "--overwrite", "--organization-name", "iknl"],
            )
        self.assertEqual(result.exit_code, 0)

        # do not overwrite
        with runner.isolated_filesystem():
            with open("privkey_iknl.pem", "w") as f:
                f.write("does-not-matter")

            result = runner.invoke(
                cli_node_create_private_key,
                ["--name", "application", "--organization-name", "iknl"],
            )

            # print(result.output)

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.common.NodeContext")
    def test_create_private_key_config_not_found(self, context):
        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_create_private_key, ["--name", "application"])

        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.clean.q")
    @patch("docker.DockerClient.volumes")
    @patch("vantage6.common.docker.addons.check_docker_running")
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

    @patch("vantage6.cli.node.common.info")
    @patch("vantage6.cli.node.common.debug")
    @patch("vantage6.cli.node.common.error")
    @patch("vantage6.cli.node.common.UserClient")
    @patch("vantage6.cli.node.common.q")
    def test_client(self, q, client, error, debug, info):
        ctx = MagicMock(
            config={
                "server_url": "localhost",
                "port": Ports.DEV_SERVER.value,
                "api_path": "",
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
