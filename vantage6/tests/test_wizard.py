import unittest

from pathlib import Path
from unittest.mock import patch, MagicMock

from vantage6.cli.configuration_wizard import (
    node_configuration_questionaire,
    server_configuration_questionaire,
    configuration_wizard,
    select_configuration_questionaire
)

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
            q.prompt.side_effect = self.prompts
            q.confirm.return_value.ask.side_effect = [True, False, True]
            dirs = MagicMock(data="/")
            config = node_configuration_questionaire(dirs, "iknl")

        keys = ["api_key", "server_url", "port", "api_path", "task_dir",
                "databases", "logging", "encryption", "vpn_subnet"]
        for key in keys:
            self.assertIn(key, config)

    def test_server_wizard(self):

        with patch(f"{module_path}.q") as q:
            q.prompt.side_effect = self.prompts
            q.confirm.return_value.ask.side_effect = [True, True, True]

            config = server_configuration_questionaire("", "vantage6")

            keys = ["description", "ip", "port", "api_path", "uri",
                    "allow_drop_all", "jwt_secret_key", "logging",
                    "vpn_server", "rabbitmq"]

            for key in keys:
                self.assertIn(key, config)

    @patch(f"{module_path}.node_configuration_questionaire")
    @patch(f"{module_path}.server_configuration_questionaire")
    @patch(f"{module_path}.ServerConfigurationManager")
    @patch(f"{module_path}.NodeConfigurationManager")
    @patch(f"{module_path}.NodeContext")
    def test_configuration_wizard_interface(self, context, node_m, server_m,
                                            server_q, node_q):
        context.instance_folders.return_value = {
            "config": "/some/path/"
        }

        file_ = configuration_wizard("node", "vtg6", "application", False)
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

        file_ = configuration_wizard("server", "vtg6", "application", True)
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

    @patch(f"{module_path}.NodeContext")
    @patch(f"{module_path}.ServerContext")
    def test_select_configuration(self, server_c, node_c):

        config = MagicMock()
        config.name = "vtg6"
        config.available_environments = ["application"]

        server_c.available_configurations.return_value = [[config], []]
        node_c.available_configurations.return_value = [[config], []]

        with patch(f"{module_path}.q") as q:
            q.select.return_value.ask.return_value = ["vtg6", "application"]
            name, env = select_configuration_questionaire("node", True)

        self.assertEqual(name, "vtg6")
        self.assertEqual(env, "application")
