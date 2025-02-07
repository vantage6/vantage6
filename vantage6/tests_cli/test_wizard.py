import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from vantage6.cli.configuration_wizard import (
    node_configuration_questionaire,
    server_configuration_questionaire,
    configuration_wizard,
    select_configuration_questionaire,
)
from vantage6.common.globals import InstanceType, NodePolicy

module_path = "vantage6.cli.configuration_wizard"


class WizardTest(unittest.TestCase):
    @staticmethod
    def prompts(*args, **kwargs):
        result = {}
        for arg in args[0]:
            name = arg["name"]
            if name == "default":  # default db path
                result[name] = "/some/path/db.sqlite"
            else:
                if "default" in arg:
                    result[name] = arg["default"]
                else:
                    result[name] = None
        return result

    def test_node_wizard(self):
        """An error is printed when docker is not running"""

        with patch(f"{module_path}.q") as q:
            q.unsafe_prompt.side_effect = self.prompts
            q.confirm.return_value.unsafe_ask.side_effect = [
                True,  # add a database
                False,  # don't enable two-factor authentication
                True,  # add VPN server
                True,  # add algorithm policies
                True,  # add single algorithms to allowed_algorithms
                "some-image",  # algorithm image to whitelist
                False,  # don't add another algorithm image
                True,  # add algorithm stores to allowed_algorithm_stores
                "some-store",  # algorithm store to whitelist
                False,  # don't add another algorithm store
                False,  # answer question on combining policies on store level and
                # single algorithm level
                False,  # don't abort if no server connection is made to pull
                # collaboration settings
                True,  # Enable encryption
            ]
            dirs = MagicMock(data="/")
            config = node_configuration_questionaire(dirs, "iknl")

        keys = [
            "api_key",
            "server_url",
            "port",
            "api_path",
            "task_dir",
            "databases",
            "logging",
            "encryption",
            "vpn_subnet",
        ]
        for key in keys:
            self.assertIn(key, config)
        nested_keys = [
            ["policies", NodePolicy.ALLOWED_ALGORITHMS],
            ["policies", NodePolicy.ALLOWED_ALGORITHM_STORES],
        ]
        for nesting in nested_keys:
            current_config = config
            for key in nesting:
                self.assertIn(key, current_config)
                current_config = current_config[key]

    def test_server_wizard(self):
        with patch(f"{module_path}.q") as q:
            q.unsafe_prompt.side_effect = self.prompts
            q.confirm.return_value.unsafe_ask.side_effect = [
                True,
                True,
                True,
                True,
                True,
                True,
                False,
            ]

            config = server_configuration_questionaire("vantage6")

            keys = [
                "description",
                "ip",
                "port",
                "api_path",
                "uri",
                "allow_drop_all",
                "jwt_secret_key",
                "logging",
                "vpn_server",
                "rabbitmq",
                "two_factor_auth",
                "algorithm_stores",
            ]

            for key in keys:
                self.assertIn(key, config)

    @patch(f"{module_path}.node_configuration_questionaire")
    @patch(f"{module_path}.server_configuration_questionaire")
    @patch(f"{module_path}.ServerConfigurationManager")
    @patch(f"{module_path}.NodeConfigurationManager")
    @patch("vantage6.cli.configuration_wizard.AppContext")
    def test_configuration_wizard_interface(
        self, context, node_m, server_m, server_q, node_q
    ):
        context.instance_folders.return_value = {"config": "/some/path/"}

        file_ = configuration_wizard(InstanceType.NODE, "vtg6", False)
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

        file_ = configuration_wizard(InstanceType.SERVER, "vtg6", True)
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

    @patch("vantage6.cli.configuration_wizard.AppContext.available_configurations")
    def test_select_configuration(self, available_configurations):
        config = MagicMock()
        config.name = "vtg6"

        available_configurations.return_value = [[config], []]

        with patch(f"{module_path}.q") as q:
            q.select.return_value.unsafe_ask.return_value = "vtg6"
            name = select_configuration_questionaire(InstanceType.NODE, True)

        self.assertEqual(name, "vtg6")
