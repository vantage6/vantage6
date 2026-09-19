import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vantage6.common.node_context import NodeContext


class NodeContextTest(unittest.TestCase):
    """Tests NodeContext's own properties and methods."""

    def setUp(self):
        self.context = object.__new__(NodeContext)
        self.context.name = "my-node"
        self.context.scope = "system"
        self.context.config = {
            "databases": {"default": "/data/default.csv", "other": "/data/other.csv"}
        }

    def test_databases_property_returns_config_databases(self):
        self.assertEqual(
            self.context.databases,
            {"default": "/data/default.csv", "other": "/data/other.csv"},
        )

    def test_get_database_uri_default_label(self):
        self.assertEqual(self.context.get_database_uri(), "/data/default.csv")

    def test_get_database_uri_explicit_label(self):
        self.assertEqual(self.context.get_database_uri("other"), "/data/other.csv")

    def test_docker_container_name(self):
        self.assertEqual(self.context.docker_container_name, "vantage6-my-node-system")

    def test_docker_network_name(self):
        self.assertEqual(
            self.context.docker_network_name, "vantage6-my-node-system-net"
        )

    def test_docker_temporary_volume_name(self):
        self.assertEqual(
            self.context.docker_temporary_volume_name(42),
            "vantage6-my-node-system-42-tmpvol",
        )

    def test_docker_volume_name_defaults_from_container_name(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.context.docker_volume_name, "vantage6-my-node-system-vol"
            )

    def test_docker_volume_name_env_var_overrides(self):
        with patch.dict(os.environ, {"DATA_VOLUME_NAME": "custom-vol"}, clear=True):
            self.assertEqual(self.context.docker_volume_name, "custom-vol")

    def test_docker_vpn_volume_name_defaults_from_container_name(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.context.docker_vpn_volume_name,
                "vantage6-my-node-system-vpn-vol",
            )

    def test_docker_vpn_volume_name_env_var_overrides(self):
        with patch.dict(os.environ, {"VPN_VOLUME_NAME": "custom-vpn"}, clear=True):
            self.assertEqual(self.context.docker_vpn_volume_name, "custom-vpn")

    def test_docker_ssh_volume_name_defaults_from_container_name(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.context.docker_ssh_volume_name,
                "vantage6-my-node-system-ssh-vol",
            )

    def test_docker_ssh_volume_name_env_var_overrides(self):
        with patch.dict(
            os.environ, {"SSH_TUNNEL_VOLUME_NAME": "custom-ssh"}, clear=True
        ):
            self.assertEqual(self.context.docker_ssh_volume_name, "custom-ssh")

    def test_docker_squid_volume_name_defaults_from_container_name(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                self.context.docker_squid_volume_name,
                "vantage6-my-node-system-squid-vol",
            )

    def test_docker_squid_volume_name_env_var_overrides(self):
        with patch.dict(
            os.environ, {"SSH_SQUID_VOLUME_NAME": "custom-squid"}, clear=True
        ):
            self.assertEqual(self.context.docker_squid_volume_name, "custom-squid")

    def test_proxy_log_file(self):
        self.context.config_manager = MagicMock()
        self.context.log_dir = Path("/logs")
        self.assertEqual(
            self.context.proxy_log_file, Path("/logs/proxy_server_system.log")
        )


if __name__ == "__main__":
    unittest.main()
