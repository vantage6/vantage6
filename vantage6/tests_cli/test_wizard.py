import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from vantage6.common.globals import FILE_BASED_DATABASE_TYPES, InstanceType, NodePolicy

from vantage6.cli.configuration_create import (
    make_configuration,
    select_configuration_questionnaire,
)
from vantage6.cli.hq.new import hq_configuration_questionaire
from vantage6.cli.node.new import node_configuration_questionaire

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
            "hq_url",
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

    @patch("vantage6.cli.configuration_create.AppContext")
    @patch("vantage6.cli.configuration_create.q")
    @patch("vantage6.cli.hq.new.q")
    def test_hq_wizard(self, q, q_hq_common, app_context):
        app_context.instance_folders.return_value = {"log": "/log"}
        q.unsafe_prompt.side_effect = self.prompts
        q_hq_common.unsafe_prompt.side_effect = self.prompts
        q_hq_common.confirm.return_value.unsafe_ask.side_effect = [
            1234,  # port
            "/data/db",  # path to database
            "postgresql://uri",  # URI of database
        ]
        q.confirm.return_value.unsafe_ask.side_effect = [
            True,  # setup allowed algorithm stores
            "https://store.uluru.vantage6.ai",  # allowed algorithm stores
        ]

        config = hq_configuration_questionaire(
            instance_name="vtg6",
            system_folders=False,
        )

        keys = ["database", "rabbitmq", "hq", "ui"]
        for key in keys:
            self.assertIn(key, config)
        nested_keys = [
            ["database", "external"],
            ["database", "uri"],
            ["database", "volumePath"],
            ["hq", "api_path"],
            ["hq", "keycloak"],
            ["hq", "logging"],
            ["hq", "port"],
            ["ui", "allowedAlgorithmStores"],
            ["rabbitmq", "password"],
        ]
        for nesting in nested_keys:
            current_config = config
            for key in nesting:
                self.assertIn(key, current_config)
                current_config = current_config[key]

    @patch("vantage6.cli.node.new.node_configuration_questionaire")
    @patch("vantage6.cli.hq.new.hq_configuration_questionaire")
    @patch("vantage6.cli.configuration_create.HQConfigurationManager")
    @patch("vantage6.cli.configuration_create.NodeConfigurationManager")
    @patch("vantage6.cli.configuration_create.AppContext")
    def test_configuration_create_interface(self, context, node_m, hq_m, hq_q, node_q):
        context.instance_folders.return_value = {"config": "/some/path/"}
        # Configure mocks to return whatever path is passed as argument - this is
        # necessary as it converts the path to a Path object and that generates Mocking
        # issues otherwise
        node_m.return_value.save.side_effect = lambda path: path
        hq_m.return_value.save.side_effect = lambda path: path

        _, file_ = make_configuration(
            config_producing_func=node_q,
            config_producing_func_args=("/some/path/", "vtg6"),
            type_=InstanceType.NODE,
            instance_name="vtg6",
            system_folders=False,
        )
        self.assertEqual(Path("/some/path/vtg6.yaml"), file_)

        _, file_ = make_configuration(
            config_producing_func=hq_q,
            config_producing_func_args=("vtg6",),
            type_=InstanceType.HQ,
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
