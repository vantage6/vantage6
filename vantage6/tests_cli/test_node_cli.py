import contextlib
import logging
import os
import unittest
from io import BytesIO, StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vantage6.common import STRING_ENCODING
from vantage6.common.globals import LOCALHOST, InstanceType, Ports

from vantage6.cli.common.utils import print_log_worker
from vantage6.cli.globals import APPNAME, InfraComponentName
from vantage6.cli.node.attach import cli_node_attach
from vantage6.cli.node.common import create_client_and_authenticate
from vantage6.cli.node.create_private_key import cli_node_create_private_key
from vantage6.cli.node.files import cli_node_files
from vantage6.cli.node.list import cli_node_list
from vantage6.cli.node.new import cli_node_new_configuration
from vantage6.cli.node.restart import cli_node_restart
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.stop import cli_node_stop


class NodeCLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        logging.getLogger("docker.utils.config").setLevel(logging.WARNING)
        return super().setUpClass()

    @patch("vantage6.cli.context.node.NodeContext.available_configurations")
    @patch("vantage6.cli.common.list.find_running_service_names")
    def test_list(self, find_running_service_names, available_configurations):
        """A container list and their current status."""
        # https://docs.python.org/3/library/unittest.mock.html#mock-names-and-the-name-attribute

        # mock that docker-deamon is running
        node_name = "iknl"
        find_running_service_names.return_value = [f"{APPNAME}-{node_name}-user-node"]

        # returns a list of configurations and failed inports
        def side_effect(system_folders):
            config = MagicMock()
            config.name = node_name
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

    @patch("vantage6.cli.common.new.select_context_and_namespace")
    @patch("vantage6.cli.common.new.make_configuration")
    @patch("vantage6.cli.common.new.ensure_config_dir_writable")
    @patch("vantage6.cli.node.common.NodeContext")
    def test_new_config(self, context, permissions, make_configuration, ctx_ns):
        """No error produced when creating new configuration."""
        context.config_exists.return_value = False
        permissions.return_value = True
        make_configuration.return_value = "/some/file/path"
        ctx_ns.return_value = ("test-context", "test-namespace")

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

    @patch("vantage6.cli.common.new.make_configuration")
    def test_new_config_replace_whitespace_in_name(self, make_configuration):
        """Whitespaces are replaced in the name."""

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some name",
            ],
        )

        self.assertTrue("[error] - Invalid name: 'some name'." in result.output)
        self.assertEqual(result.exit_code, 1)

    # the context is mocked for select_context_class where it is instantiated
    @patch("vantage6.cli.common.new.select_context_and_namespace")
    @patch("vantage6.cli.context.NodeContext")
    def test_new_config_already_exists(self, context, ctx_ns):
        """No duplicate configurations are allowed."""

        context.config_exists.return_value = True
        ctx_ns.return_value = ("test-context", "test-namespace")

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some-name",
            ],
        )

        # check that error is produced
        self.assertIn(
            "[error] - Configuration some-name already exists!", result.output
        )

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.common.new.select_context_and_namespace")
    @patch("vantage6.cli.common.new.ensure_config_dir_writable")
    @patch("vantage6.cli.node.common.NodeContext")
    def test_new_write_permissions(self, context, permissions, ctx_ns):
        """User needs write permissions."""

        context.config_exists.return_value = False
        permissions.return_value = False
        ctx_ns.return_value = ("test-context", "test-namespace")

        runner = CliRunner()
        result = runner.invoke(
            cli_node_new_configuration,
            [
                "--name",
                "some-name",
            ],
        )

        # check that error is produced
        self.assertTrue("[error] - Your user does not have write" in result.output)

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.common.decorator.get_context")
    @patch("vantage6.cli.common.decorator.select_configuration_questionnaire")
    def test_files(self, select_config, context):
        """No errors produced when retrieving filepaths."""

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

    @patch("vantage6.cli.node.start.select_context_and_namespace")
    @patch("os.makedirs")
    @patch("vantage6.cli.common.decorator.get_context")
    @patch("vantage6.cli.node.start.helm_install")
    @patch("vantage6.cli.node.start.start_port_forward")
    def test_start(
        self,
        start_port_forward,
        helm_install,
        context,
        os_makedirs,
        ctx_ns,
    ):
        """Start node without errors"""

        ctx = MagicMock(
            config={"node": {"proxyPort": 8080}},
            config_file="/config.yaml",
            data_dir=Path("."),
            log_dir=Path("."),
            helm_release_name="vantage6-test-node",
            is_sandbox=False,
        )
        ctx.config_exists.return_value = True
        ctx.name = "test-node"
        context.return_value = ctx
        ctx_ns.return_value = ("test-context", "test-namespace")

        runner = CliRunner()
        result = runner.invoke(cli_node_start, ["--name", "test-node"])

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.common.stop.select_context_and_namespace")
    @patch("vantage6.cli.common.stop.get_context")
    @patch("vantage6.cli.common.utils.find_running_service_names")
    @patch("vantage6.cli.node.stop._stop_node")
    def test_stop(self, _stop_node, find_running_service_names, get_context, ctx_ns):
        node_name = "iknl"
        node_helm_name = f"{APPNAME}-{node_name}-user-node"
        find_running_service_names.return_value = [node_helm_name]
        get_context.return_value = MagicMock(helm_release_name=node_helm_name)
        ctx_ns.return_value = ("test-context", "test-namespace")

        runner = CliRunner()
        result = runner.invoke(cli_node_stop, ["--name", "iknl"])

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.exception)

    @patch("vantage6.cli.common.stop.select_context_and_namespace")
    @patch("vantage6.cli.node.restart.select_context_and_namespace")
    @patch("vantage6.cli.node.restart.subprocess.run")
    @patch("vantage6.cli.common.stop.get_context")
    @patch("vantage6.cli.node.stop._stop_node")
    def test_restart(
        self, _stop_node, get_context, subprocess_run, ctx_ns_stop, ctx_ns_restart
    ):
        """Restart a node without errors."""
        node_name = "iknl"
        node_helm_name = f"{APPNAME}-{node_name}-user-node"
        get_context.return_value = MagicMock(helm_release_name=node_helm_name)
        ctx_ns_stop.return_value = ("test-context", "test-namespace")
        ctx_ns_restart.return_value = ("test-context", "test-namespace")

        # Mock subprocess.run to handle both helm calls and node start calls
        def mock_subprocess_run(*args, **kwargs):
            # Check if this is a helm command (contains 'helm list')
            if "helm" in args[0] and "list" in args[0]:
                return MagicMock(
                    stdout='[{"name": "' + node_helm_name + '", "status": "deployed"}]',
                    returncode=0,
                )
            else:
                # For other subprocess calls (like starting the node)
                return MagicMock(returncode=0)

        subprocess_run.side_effect = mock_subprocess_run
        runner = CliRunner()
        result = runner.invoke(cli_node_restart, ["--name", "iknl"])
        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.attach.attach_logs")
    def test_attach(self, attach_logs):
        """Attach docker logs without errors."""
        runner = CliRunner()
        runner.invoke(cli_node_attach)
        attach_logs.assert_called_once_with(
            name=None,
            instance_type=InstanceType.NODE,
            infra_component=InfraComponentName.NODE,
            system_folders=False,
            context=None,
            namespace=None,
            is_sandbox=False,
        )

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

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.common.NodeContext")
    def test_create_private_key_config_not_found(self, context):
        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_create_private_key, ["--name", "application"])

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
    def test_client(self, client, error, debug, info):
        ctx = MagicMock(
            config={
                "node": {
                    "server": {
                        "url": LOCALHOST,
                        "port": Ports.DEV_SERVER.value,
                        "path": "",
                    }
                }
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
