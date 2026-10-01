import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from vantage6.common.encryption import RSACryptor
from vantage6.common.globals import LOCALHOST, InstanceType, Ports

from vantage6.cli.globals import APPNAME, InfraComponentName
from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.node.attach import cli_node_attach
from vantage6.cli.node.common import create_client_and_authenticate
from vantage6.cli.node.common.private_key import public_key_base64_from_pem
from vantage6.cli.node.create_private_key import cli_node_create_private_key
from vantage6.cli.node.files import cli_node_files
from vantage6.cli.node.list import cli_node_list
from vantage6.cli.node.new import cli_node_new_configuration
from vantage6.cli.node.remove import cli_node_remove
from vantage6.cli.node.restart import cli_node_restart
from vantage6.cli.node.start import cli_node_start
from vantage6.cli.node.stop import cli_node_stop

TEST_PRIVATE_KEY_PEM = RSACryptor.create_new_rsa_key_pem()
OTHER_PRIVATE_KEY_PEM = RSACryptor.create_new_rsa_key_pem()


class NodeCLITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        return super().setUpClass()

    @patch("vantage6.cli.common.list.running_in_wsl", return_value=False)
    @patch("vantage6.cli.context.node.NodeContext.available_configurations")
    @patch("vantage6.cli.common.list.find_running_service_names")
    def test_list(
        self, find_running_service_names, available_configurations, _running_in_wsl
    ):
        """A container list and their current status."""
        # https://docs.python.org/3/library/unittest.mock.html#mock-names-and-the-name-attribute

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

    @patch("vantage6.cli.common.new.make_configuration")
    @patch("vantage6.cli.common.new.ensure_config_dir_writable")
    @patch("vantage6.cli.node.common.NodeContext")
    def test_new_config(self, context, permissions, make_configuration):
        """No error produced when creating new configuration."""
        context.config_exists.return_value = False
        permissions.return_value = True
        make_configuration.return_value = (
            {"node": {"encryption": {"enabled": False}}},
            "/some/file/path",
        )

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

    def _run_encrypted_wizard(self, hq_public_key, confirm=True, key_path=""):
        """Run `v6 node new` with encryption enabled; return the create-key mock."""
        mod = "vantage6.cli.node.new"
        with (
            patch("vantage6.cli.node.common.NodeContext") as context,
            patch("vantage6.cli.common.new.ensure_config_dir_writable") as writable,
            patch("vantage6.cli.common.new.make_configuration") as make_config,
            patch(f"{mod}.q") as q,
            patch(f"{mod}.NodeContext"),
            patch(f"{mod}.select_k8s_config"),
            patch(f"{mod}.create_client_and_authenticate"),
            patch(f"{mod}.get_organization_public_key", return_value=hq_public_key),
            patch(f"{mod}.create_and_store_private_key") as create_key,
        ):
            context.config_exists.return_value = False
            writable.return_value = True
            make_config.return_value = (
                {"node": {"encryption": {"enabled": True}}},
                "/some/file/path",
            )
            q.confirm.return_value.unsafe_ask.return_value = confirm
            q.path.return_value.unsafe_ask.return_value = key_path
            result = CliRunner().invoke(
                cli_node_new_configuration, ["--name", "some-name"]
            )
        self.assertEqual(result.exit_code, 0, result.output)
        return create_key

    def test_new_config_encrypted_new_organization_key(self):
        """No key at HQ: the wizard offers to generate one."""
        create_key = self._run_encrypted_wizard(hq_public_key=None, confirm=True)
        create_key.assert_called_once()
        self.assertIsNone(create_key.call_args.kwargs["pem"])

        create_key = self._run_encrypted_wizard(hq_public_key=None, confirm=False)
        create_key.assert_not_called()

    def test_new_config_encrypted_existing_organization_key(self):
        """Key at HQ: the wizard asks for the existing key instead of generating."""
        hq_key = public_key_base64_from_pem(TEST_PRIVATE_KEY_PEM)
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("org_key.pem").write_bytes(TEST_PRIVATE_KEY_PEM)
            create_key = self._run_encrypted_wizard(hq_key, key_path="org_key.pem")
            create_key.assert_called_once()
            self.assertEqual(create_key.call_args.kwargs["pem"], TEST_PRIVATE_KEY_PEM)

            # skipping the question does not create a key
            create_key = self._run_encrypted_wizard(hq_key, key_path="")
            create_key.assert_not_called()

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
    @patch("vantage6.cli.context.NodeContext")
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
        self.assertIn(
            "[error] - Configuration some-name already exists!", result.output
        )

        # check non-zero exit code
        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.common.new.ensure_config_dir_writable")
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

    @patch("vantage6.cli.node.start.select_k8s_config")
    @patch("os.makedirs")
    @patch("vantage6.cli.common.decorator.get_context")
    @patch("vantage6.cli.node.start.helm_install")
    def test_start(
        self,
        helm_install,
        context,
        os_makedirs,
        ctx_ns,
    ):
        """Start node without errors"""

        ctx = MagicMock(
            config={"node": {"proxyPort": 7654, "image": "my-node-image"}},
            config_file="/config.yaml",
            data_dir=Path("."),
            log_dir=Path("."),
            helm_release_name="vantage6-test-node",
            is_sandbox=False,
        )
        ctx.config_exists.return_value = True
        ctx.name = "test-node"
        context.return_value = ctx
        ctx_ns.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )

        runner = CliRunner()
        result = runner.invoke(cli_node_start, ["--name", "test-node"])

        self.assertEqual(result.exit_code, 0)

    @patch("vantage6.cli.node.start.private_key_secret_exists")
    @patch("vantage6.cli.node.start.select_k8s_config")
    @patch("os.makedirs")
    @patch("vantage6.cli.common.decorator.get_context")
    @patch("vantage6.cli.node.start.helm_install")
    def test_start_encrypted_without_private_key_secret(
        self, helm_install, context, os_makedirs, ctx_ns, secret_exists
    ):
        """Node with encryption enabled must not start without its key secret"""
        ctx = MagicMock(
            config={
                "node": {"image": "my-node-image", "encryption": {"enabled": True}}
            },
            helm_release_name="vantage6-test-node",
            is_sandbox=False,
        )
        ctx.config_exists.return_value = True
        ctx.name = "test-node"
        context.return_value = ctx
        ctx_ns.return_value = KubernetesConfig(context="ctx", namespace="ns")
        secret_exists.return_value = False

        result = CliRunner().invoke(cli_node_start, ["--name", "test-node"])

        self.assertEqual(result.exit_code, 1)
        helm_install.assert_not_called()

        secret_exists.return_value = True
        result = CliRunner().invoke(cli_node_start, ["--name", "test-node"])
        self.assertEqual(result.exit_code, 0, result.output)
        helm_install.assert_called_once()

    @patch("vantage6.cli.node.remove.delete_private_key_secret")
    @patch("vantage6.cli.node.remove.select_k8s_config")
    @patch("vantage6.cli.node.remove.execute_remove")
    @patch("vantage6.cli.common.decorator.get_context")
    def test_remove_deletes_private_key_secret(
        self, context, execute_remove, ctx_ns, delete_secret
    ):
        ctx = MagicMock(helm_release_name="vantage6-test-node", config_dir=Path("/x"))
        ctx.config_exists.return_value = True
        context.return_value = ctx
        ctx_ns.return_value = KubernetesConfig(context="ctx", namespace="ns")
        delete_secret.return_value = True

        result = CliRunner().invoke(cli_node_remove, ["--name", "test-node", "-f"])

        self.assertEqual(result.exit_code, 0, result.output)
        execute_remove.assert_called_once()
        delete_secret.assert_called_once_with(ctx, ctx_ns.return_value)

    @patch("vantage6.cli.common.stop.select_k8s_config")
    @patch("vantage6.cli.common.stop.get_context")
    @patch("vantage6.cli.common.utils.find_running_service_names")
    @patch("vantage6.cli.node.stop._stop_node")
    def test_stop(self, _stop_node, find_running_service_names, get_context, ctx_ns):
        node_name = "iknl"
        node_helm_name = f"{APPNAME}-{node_name}-user-node"
        find_running_service_names.return_value = [node_helm_name]
        get_context.return_value = MagicMock(helm_release_name=node_helm_name)
        ctx_ns.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )

        runner = CliRunner()
        result = runner.invoke(cli_node_stop, ["--name", "iknl"])

        self.assertEqual(result.exit_code, 0)
        self.assertIsNone(result.exception)

    @patch("vantage6.cli.common.stop.select_k8s_config")
    @patch("vantage6.cli.node.restart.select_k8s_config")
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
        ctx_ns_stop.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )
        ctx_ns_restart.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )

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
    @patch("vantage6.cli.node.attach.select_k8s_config")
    def test_attach(self, select_k8s_config, attach_logs):
        """Attach pod logs without errors."""
        select_k8s_config.return_value = KubernetesConfig(
            context="test-context",
            namespace="test-namespace",
        )
        runner = CliRunner()
        runner.invoke(cli_node_attach)
        attach_logs.assert_called_once_with(
            name=None,
            instance_type=InstanceType.NODE,
            infra_component=InfraComponentName.NODE,
            system_folders=False,
            k8s_config=KubernetesConfig(
                context="test-context",
                namespace="test-namespace",
            ),
            is_sandbox=False,
        )

    def _run_create_private_key(self, args, hq_public_key=None, existing=None):
        """
        Invoke create-private-key with Kubernetes and HQ mocked.

        Returns the result, the files written to the working directory and the
        mocks for writing the secret and for the HQ client.
        """
        mod = "vantage6.cli.node.create_private_key"
        client = MagicMock(whoami=MagicMock(organization_id=3))

        def request(path, method="get", json=None):
            if method == "get":
                return {"public_key": hq_public_key or ""}
            return {}

        client.request.side_effect = request
        with (
            patch("vantage6.cli.node.common.NodeContext") as common_ctx,
            patch(f"{mod}.NodeContext") as context,
            patch(f"{mod}.select_k8s_config") as k8s_cfg,
            patch(f"{mod}.create_client_and_authenticate", return_value=client),
            patch(f"{mod}.read_private_key_secret", return_value=existing),
            patch(f"{mod}.write_private_key_secret") as write,
            patch(f"{mod}.q") as q,
        ):
            common_ctx.config_exists.return_value = True
            context.return_value = MagicMock(is_sandbox=False)
            k8s_cfg.return_value = KubernetesConfig(context="ctx", namespace="ns")
            self.confirm = q.confirm.return_value.unsafe_ask
            self.confirm.return_value = self.confirm_answer
            runner = CliRunner()
            with runner.isolated_filesystem():
                Path("org_key.pem").write_bytes(TEST_PRIVATE_KEY_PEM)
                Path("other_key.pem").write_bytes(OTHER_PRIVATE_KEY_PEM)
                Path("invalid.pem").write_text("not a key")
                result = runner.invoke(
                    cli_node_create_private_key, ["--name", "application", *args]
                )
                files_written = sorted(os.listdir("."))
        return result, files_written, write, client

    def _uploads(self, client):
        return [
            c
            for c in client.request.call_args_list
            if c.kwargs.get("method") == "patch"
        ]

    confirm_answer = True
    HQ_KEY = public_key_base64_from_pem(TEST_PRIVATE_KEY_PEM)

    def test_create_private_key_new_organization(self):
        """No key at HQ: key is generated into the secret, no file, upload."""
        result, files, write, client = self._run_create_private_key([])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(files, ["invalid.pem", "org_key.pem", "other_key.pem"])
        write.assert_called_once()
        pem = write.call_args.args[2]
        uploads = self._uploads(client)
        self.assertEqual(len(uploads), 1)
        self.assertEqual(
            uploads[0].kwargs["json"], {"public_key": public_key_base64_from_pem(pem)}
        )

    def test_create_private_key_refuses_new_key_if_org_has_one(self):
        result, _, write, client = self._run_create_private_key(
            [], hq_public_key=self.HQ_KEY
        )

        self.assertEqual(result.exit_code, 1)
        write.assert_not_called()
        self.assertEqual(self._uploads(client), [])

    def test_create_private_key_from_file_matching_org_key(self):
        result, _, write, client = self._run_create_private_key(
            ["--from-file", "org_key.pem"], hq_public_key=self.HQ_KEY
        )

        self.assertEqual(result.exit_code, 0, result.output)
        write.assert_called_once()
        self.assertEqual(write.call_args.args[2], TEST_PRIVATE_KEY_PEM)
        # HQ already has the matching public key: nothing to upload
        self.assertEqual(self._uploads(client), [])

    def test_create_private_key_from_file_not_matching_org_key(self):
        result, _, write, client = self._run_create_private_key(
            ["--from-file", "other_key.pem"], hq_public_key=self.HQ_KEY
        )

        self.assertEqual(result.exit_code, 1)
        write.assert_not_called()
        self.assertEqual(self._uploads(client), [])

    def test_create_private_key_replace_organization_key(self):
        self.confirm_answer = True
        result, _, write, client = self._run_create_private_key(
            ["--replace-organization-key"], hq_public_key=self.HQ_KEY
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.confirm.assert_called_once()
        write.assert_called_once()
        self.assertEqual(len(self._uploads(client)), 1)

        # declining the confirmation changes nothing
        self.confirm_answer = False
        result, _, write, client = self._run_create_private_key(
            ["--replace-organization-key"], hq_public_key=self.HQ_KEY
        )
        self.assertEqual(result.exit_code, 0, result.output)
        write.assert_not_called()
        self.assertEqual(self._uploads(client), [])

    def test_create_private_key_existing_secret_is_kept(self):
        result, _, write, client = self._run_create_private_key(
            [], hq_public_key=self.HQ_KEY, existing=TEST_PRIVATE_KEY_PEM
        )

        self.assertEqual(result.exit_code, 0, result.output)
        write.assert_not_called()
        self.assertEqual(self._uploads(client), [])

    def test_create_private_key_no_upload(self):
        result, _, write, client = self._run_create_private_key(["--no-upload"])

        self.assertEqual(result.exit_code, 0, result.output)
        write.assert_called_once()
        client.request.assert_not_called()

    def test_create_private_key_invalid_file(self):
        result, _, write, _ = self._run_create_private_key(
            ["--from-file", "invalid.pem"]
        )

        self.assertEqual(result.exit_code, 1)
        write.assert_not_called()

    @patch("vantage6.cli.node.common.NodeContext")
    def test_create_private_key_config_not_found(self, context):
        context.config_exists.return_value = False

        runner = CliRunner()
        result = runner.invoke(cli_node_create_private_key, ["--name", "application"])

        self.assertEqual(result.exit_code, 1)

    @patch("vantage6.cli.node.common.info")
    @patch("vantage6.cli.node.common.debug")
    @patch("vantage6.cli.node.common.error")
    @patch("vantage6.cli.node.common.UserClient")
    def test_client(self, client, error, debug, info):
        ctx = MagicMock(
            config={
                "node": {
                    "hq": {
                        "url": LOCALHOST,
                        "port": Ports.DEV_HQ.value,
                        "path": "",
                    }
                }
            }
        )

        # should not trigger an exception
        create_client_and_authenticate(ctx)
