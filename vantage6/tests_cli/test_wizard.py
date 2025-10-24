import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vantage6.common.globals import FILE_BASED_DATABASE_TYPES, InstanceType, NodePolicy

from vantage6.cli.configuration_create import (
    make_configuration,
    select_configuration_questionnaire,
)
from vantage6.cli.node.new import node_configuration_questionaire
from vantage6.cli.server.new import server_configuration_questionaire

module_path = "vantage6.cli.configuration_create"


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

    @patch("vantage6.cli.node.new.q")
    @patch("vantage6.cli.node.new.NodeClient.authenticate")
    def test_node_wizard(self, authenticate, q):
        """Check the node wizard runs without errors."""
        q.unsafe_prompt.side_effect = self.prompts
        q.confirm.return_value.unsafe_ask.side_effect = [
            True,  # add a database
            "Database reachable by URI",  # type of database to add
            "http://localhost:5000",  # URI of database
            FILE_BASED_DATABASE_TYPES[0],  # type of database
            False,  # don't add environment variables
            False,  # don't add another database
            True,  # add algorithm policies
            True,  # add list of allowed_algorithms
            "some-image",  # algorithm image to whitelist
            False,  # don't add another algorithm image
            True,  # add algorithm stores to allowed_algorithm_stores
            "some-store",  # algorithm store to whitelist
            False,  # don't add another algorithm store
            False,  # answer question on combining policies on store level and
            # single algorithm level
            "DEBUG",  # level of logging
            True,  # Enable encryption
            "privkey_Test.pem",  # path to private key file
        ]
        authenticate.side_effect = None
        config = node_configuration_questionaire(
            data_dir="/data", instance_name="iknl", log_dir="/log"
        )

        keys = [
            "api_key",
            "api_path",
            "databases",
            "encryption",
            "logging",
            "port",
            "server_url",
            "task_dir",
        ]
        for key in keys:
            self.assertIn(key, config["node"])
        nested_keys = [
            ["policies", NodePolicy.ALLOWED_ALGORITHMS.value],
            ["policies", NodePolicy.ALLOWED_ALGORITHM_STORES.value],
            ["encryption", "private_key"],
            ["encryption", "enabled"],
            ["logging", "loggers"],
            ["databases", "fileBased"],
            ["databases", "serviceBased"],
        ]
        for nesting in nested_keys:
            current_config = config["node"]
            for key in nesting:
                self.assertIn(key, current_config)
                current_config = current_config[key]
        assert len(config["node"]["databases"]["fileBased"]) == 0
        assert len(config["node"]["databases"]["serviceBased"]) == 1

    @patch("vantage6.cli.configuration_create.q")
    @patch("vantage6.cli.server.new.q")
    def test_server_wizard(self, q, q_server_common):
        q.unsafe_prompt.side_effect = self.prompts
        q_server_common.unsafe_prompt.side_effect = self.prompts
        q_server_common.confirm.return_value.unsafe_ask.side_effect = [
            1234,  # port
            "DEBUG",  # level of logging
            "/data/db",  # path to database
            "docker-desktop",  # name of k8s node
            True,  # use production settings
            "postgresql://uri",  # URI of database
        ]
        q.confirm.return_value.unsafe_ask.side_effect = [
            "server-image",  # server image
            "ui-image",  # UI image
        ]

        config = server_configuration_questionaire(instance_name="vtg6", log_dir="/log")

        keys = ["database", "rabbitmq", "server", "ui"]
        for key in keys:
            self.assertIn(key, config)
        nested_keys = [
            ["database", "external"],
            ["database", "k8sNodeName"],
            ["database", "uri"],
            ["database", "volumePath"],
            ["server", "api_path"],
            ["server", "image"],
            ["server", "keycloakUrl"],
            ["server", "logging", "level"],
            ["server", "port"],
            ["ui", "image"],
        ]
        for nesting in nested_keys:
            current_config = config
            for key in nesting:
                self.assertIn(key, current_config)
                current_config = current_config[key]

    @patch("vantage6.cli.node.new.node_configuration_questionaire")
    @patch("vantage6.cli.server.new.server_configuration_questionaire")
    @patch("vantage6.cli.configuration_create.ServerConfigurationManager")
    @patch("vantage6.cli.configuration_create.NodeConfigurationManager")
    @patch("vantage6.cli.configuration_create.AppContext")
    def test_configuration_create_interface(
        self, context, node_m, server_m, server_q, node_q
    ):
        context.instance_folders.return_value = {"config": "/some/path/"}
        # Configure mocks to return whatever path is passed as argument - this is
        # necessary as it converts the path to a Path object and that generates Mocking
        # issues otherwise
        node_m.return_value.save.side_effect = lambda path: path
        server_m.return_value.save.side_effect = lambda path: path

        file_ = make_configuration(
            config_producing_func=node_q,
            config_producing_func_args=("/some/path/", "vtg6"),
            type_=InstanceType.NODE,
            instance_name="vtg6",
            system_folders=False,
        )
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

        file_ = make_configuration(
            config_producing_func=server_q,
            config_producing_func_args=("vtg6",),
            type_=InstanceType.SERVER,
            instance_name="vtg6",
            system_folders=True,
        )
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

    @patch("vantage6.cli.configuration_create.AppContext.available_configurations")
    def test_select_configuration(self, available_configurations):
        config = MagicMock()
        config.name = "vtg6"

        available_configurations.return_value = [[config], []]

        with patch(f"{module_path}.q") as q:
            q.select.return_value.unsafe_ask.return_value = "vtg6"
            name = select_configuration_questionnaire(InstanceType.NODE, True)

        self.assertEqual(name, "vtg6")
