import subprocess
import unittest
from unittest.mock import MagicMock, call, patch

import click
from click.testing import CliRunner

from vantage6.cli.auth.install import (
    SUPPORTED_KEYCLOAK_OPERATOR_VERSION,
    _wait_for_operator_ready,
    check_and_install_keycloak_operator,
    cli_auth_install_operator,
)
from vantage6.cli.k8s_config import KubernetesConfig


class AuthInstallTest(unittest.TestCase):
    def setUp(self):
        self.runner = CliRunner()
        self.k8s_config = KubernetesConfig(context="test-context", namespace="test-ns")

    def _invoke_install(self, version=None):
        args = [] if version is None else ["--operator-version", version]
        with (
            patch(
                "vantage6.cli.auth.install.select_k8s_config",
                return_value=self.k8s_config,
            ),
            patch("vantage6.cli.auth.install.run_kubectl_command") as kubectl,
            patch("vantage6.cli.auth.install._wait_for_operator_ready"),
        ):
            result = self.runner.invoke(cli_auth_install_operator, args)
        return result, kubectl

    def _applied_manifest_names(self, kubectl):
        return [
            invocation.args[0][2].rsplit("/", 1)[-1]
            for invocation in kubectl.call_args_list
            if invocation.args[0][:2] == ["apply", "-f"]
        ]

    def test_default_installs_supported_legacy_manifests_in_order(self):
        result, kubectl = self._invoke_install()

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(SUPPORTED_KEYCLOAK_OPERATOR_VERSION, "26.6.2")
        self.assertEqual(
            self._applied_manifest_names(kubectl),
            [
                "keycloaks.k8s.keycloak.org-v1.yml",
                "keycloakrealmimports.k8s.keycloak.org-v1.yml",
                "kubernetes.yml",
            ],
        )

    def test_26_7_and_later_install_client_crds(self):
        expected = [
            "keycloaks.k8s.keycloak.org-v1.yml",
            "keycloakrealmimports.k8s.keycloak.org-v1.yml",
            "keycloakoidcclients.k8s.keycloak.org-v1.yml",
            "keycloaksamlclients.k8s.keycloak.org-v1.yml",
            "kubernetes.yml",
        ]

        for version in ("26.7.0", "27.0.0"):
            with self.subTest(version=version):
                result, kubectl = self._invoke_install(version)
                self.assertEqual(result.exit_code, 0, result.output)
                self.assertEqual(self._applied_manifest_names(kubectl), expected)

    def test_pre_26_7_does_not_install_client_crds(self):
        result, kubectl = self._invoke_install("26.6.9")

        self.assertEqual(result.exit_code, 0, result.output)
        applied = self._applied_manifest_names(kubectl)
        self.assertNotIn("keycloakoidcclients.k8s.keycloak.org-v1.yml", applied)
        self.assertNotIn("keycloaksamlclients.k8s.keycloak.org-v1.yml", applied)

    def test_skip_crds_still_installs_operator_manifest(self):
        with (
            patch(
                "vantage6.cli.auth.install.select_k8s_config",
                return_value=self.k8s_config,
            ),
            patch("vantage6.cli.auth.install.run_kubectl_command") as kubectl,
            patch("vantage6.cli.auth.install._wait_for_operator_ready"),
        ):
            result = self.runner.invoke(cli_auth_install_operator, ["--skip-crds"])

        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(self._applied_manifest_names(kubectl), ["kubernetes.yml"])

    @patch("vantage6.cli.auth.install.select_k8s_config")
    def test_malformed_version_fails_before_cluster_access(self, select_k8s_config):
        result = self.runner.invoke(
            cli_auth_install_operator, ["--operator-version", "26.7"]
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("major.minor.patch", result.output)
        select_k8s_config.assert_not_called()

    @patch("vantage6.cli.auth.install._wait_for_operator_ready")
    @patch("vantage6.cli.auth.install.run_kubectl_command")
    @patch("vantage6.cli.auth.install.select_k8s_config")
    def test_required_manifest_failure_aborts_install(
        self, select_k8s_config, kubectl, wait_for_ready
    ):
        select_k8s_config.return_value = self.k8s_config
        kubectl.side_effect = subprocess.CalledProcessError(1, ["kubectl"])

        result = self.runner.invoke(cli_auth_install_operator)

        self.assertNotEqual(result.exit_code, 0)
        self.assertEqual(kubectl.call_count, 1)
        wait_for_ready.assert_not_called()
        self.assertNotIn("installed successfully", result.output)

    @patch("vantage6.cli.auth.install.subprocess.run")
    @patch("vantage6.cli.auth.install.time.sleep")
    @patch("vantage6.cli.auth.install.time.time", side_effect=[0, 0, 1])
    def test_wait_for_operator_ready_returns_on_success(
        self, _time, _sleep, run
    ):
        run.return_value = MagicMock(stdout="True\n")

        _wait_for_operator_ready("test-ns", self.k8s_config, timeout=1)

        run.assert_called_once()

    @patch("vantage6.cli.auth.install.subprocess.run")
    @patch("vantage6.cli.auth.install.time.sleep")
    @patch("vantage6.cli.auth.install.time.time", side_effect=[0, 0, 2])
    def test_wait_for_operator_ready_raises_on_timeout(self, _time, _sleep, run):
        run.return_value = MagicMock(stdout="False")

        with self.assertRaises(click.ClickException):
            _wait_for_operator_ready("test-ns", self.k8s_config, timeout=1)

    @patch("vantage6.cli.auth.install._wait_for_operator_ready")
    @patch("vantage6.cli.auth.install.run_kubectl_command")
    @patch("vantage6.cli.auth.install.select_k8s_config")
    def test_cli_timeout_does_not_report_success(
        self, select_k8s_config, _kubectl, wait_for_ready
    ):
        select_k8s_config.return_value = self.k8s_config
        wait_for_ready.side_effect = click.ClickException("operator timeout")

        result = self.runner.invoke(cli_auth_install_operator)

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("operator timeout", result.output)
        self.assertNotIn("installed successfully in namespace", result.output)

    @patch("vantage6.cli.auth.install.subprocess.run")
    @patch("vantage6.cli.auth.install._check_keycloak_operator_installed")
    @patch("vantage6.cli.auth.install.select_k8s_config")
    def test_sandbox_preflight_stops_when_installer_fails(
        self, select_k8s_config, operator_installed, run
    ):
        select_k8s_config.return_value = self.k8s_config
        operator_installed.return_value = False
        run.return_value = MagicMock(returncode=1)

        with self.assertRaises(SystemExit) as raised:
            check_and_install_keycloak_operator(self.k8s_config)

        self.assertEqual(raised.exception.code, 1)
        self.assertEqual(
            run.call_args,
            call(
                [
                    "v6",
                    "auth",
                    "install-keycloak",
                    "--context",
                    "test-context",
                    "--namespace",
                    "test-ns",
                ],
                check=False,
            ),
        )


if __name__ == "__main__":
    unittest.main()
