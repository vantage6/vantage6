import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from jinja2 import Environment, FileSystemLoader

from vantage6.common.globals import (
    APPNAME,
    FILE_BASED_DATABASE_TYPES,
    InstanceType,
    NodePolicy,
)

from vantage6.cli.configuration_create import (
    make_configuration,
    select_configuration_questionnaire,
)
from vantage6.cli.globals import PACKAGE_FOLDER
from vantage6.cli.hq.new import hq_configuration_questionaire
from vantage6.cli.node.new import (
    _get_algorithm_policies,
    node_configuration_questionaire,
)

module_path = "vantage6.cli.configuration_create"


class _ScriptedQuestionary:
    """
    Stand-in for the questionary module. Prompts are answered from ``prompts`` or
    their defaults; confirm, select and text questions from their queues in order.
    """

    def __init__(self, prompts: dict, confirms: list, selects: list, texts: list):
        self.prompts = prompts
        self.confirms = list(confirms)
        self.selects = list(selects)
        self.texts = list(texts)

    def unsafe_prompt(self, questions: list[dict]) -> dict:
        return {
            question["name"]: self.prompts.get(
                question["name"], question.get("default")
            )
            for question in questions
        }

    @staticmethod
    def _answer(queue: list) -> MagicMock:
        question = MagicMock()
        question.unsafe_ask.side_effect = lambda: queue.pop(0)
        return question

    def confirm(self, *args, **kwargs) -> MagicMock:
        return self._answer(self.confirms)

    def select(self, *args, **kwargs) -> MagicMock:
        return self._answer(self.selects)

    def text(self, *args, **kwargs) -> MagicMock:
        return self._answer(self.texts)


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

    @patch("vantage6.cli.node.new.NodeClient.authenticate")
    def test_node_wizard(self, authenticate):
        """The node wizard produces values for the node Helm chart."""
        config = self._run_node_wizard(authenticate)

        node = config["node"]
        self.assertEqual(node["name"], "iknl")
        self.assertEqual(node["apiKey"], "my-api-key")
        self.assertEqual(node["hq"]["url"], "https://hq.example.org")
        self.assertEqual(node["keycloak"]["url"], "https://auth.example.org")
        self.assertEqual(
            node["persistence"]["tasks"],
            {"storageClass": "cephfs", "size": "10Gi", "accessMode": "ReadWriteMany"},
        )
        self.assertEqual(
            node["databases"]["fileBased"],
            [
                {
                    "name": "default",
                    "type": FILE_BASED_DATABASE_TYPES[0],
                    "existingClaim": "hospital-data",
                    "subPath": "exports/data.csv",
                }
            ],
        )
        self.assertEqual(
            node["networkPolicy"], {"enabled": False, "verifyIsolation": False}
        )
        self.assertEqual(node["resources"]["limits"]["memory"], "4Gi")
        self.assertEqual(
            node["algorithmPods"]["resources"]["requests"]["ephemeral-storage"], "1Gi"
        )
        self.assertEqual(
            node["policies"][NodePolicy.ALLOWED_ALGORITHMS.value], ["some-image"]
        )
        self.assertTrue(node["encryption"]["enabled"])
        for key in ("task_dir", "api_key", "hq_url", "taskNamespace"):
            self.assertNotIn(key, node)
        self.assertNotIn("volumeHostPath", node["logging"])
        # the private key lives in a Kubernetes secret, not in the configuration
        self.assertNotIn("private_key", node["encryption"])

    @patch("vantage6.cli.node.new.NodeClient.authenticate")
    def test_node_wizard_output_renders_chart_values(self, authenticate):
        """The wizard's answers render to a values file without host paths."""
        config = self._run_node_wizard(authenticate)

        environment = Environment(
            loader=FileSystemLoader(PACKAGE_FOLDER / APPNAME / "cli" / "template"),
            trim_blocks=True,
            lstrip_blocks=True,
            autoescape=True,
        )
        values = yaml.safe_load(
            environment.get_template("node_config.j2").render(config)
        )

        node = values["node"]
        self.assertEqual(node["apiKey"], "my-api-key")
        self.assertEqual(node["keycloak"]["url"], "https://auth.example.org")
        self.assertEqual(node["persistence"]["tasks"]["storageClass"], "cephfs")
        self.assertEqual(node["persistence"]["tasks"]["accessMode"], "ReadWriteMany")
        self.assertNotIn("hostPath", node["persistence"]["tasks"])
        self.assertNotIn("database", node["persistence"])
        self.assertNotIn("k8sNodeName", node)
        self.assertNotIn("taskNamespace", node)
        self.assertNotIn("volumeHostPath", node["logging"])
        self.assertEqual(node["logging"]["storageClass"], "")
        self.assertEqual(
            node["databases"]["fileBased"][0]["existingClaim"], "hospital-data"
        )
        self.assertNotIn("volumePath", node["databases"]["fileBased"][0])
        self.assertFalse(node["networkPolicy"]["enabled"])
        self.assertEqual(node["networkPolicy"]["dns"]["ports"], [53])
        self.assertEqual(node["resources"]["limits"]["cpu"], "2")
        self.assertEqual(node["algorithmPods"]["ttlSecondsAfterFinished"], 86400)
        self.assertEqual(node["algorithmPods"]["resources"]["limits"]["memory"], "8Gi")

    @patch("vantage6.cli.node.new.NodeClient.authenticate")
    def test_docker_node_wizard(self, authenticate):
        """A Docker node gets host paths and container limits, no Kubernetes keys."""
        authenticate.side_effect = None
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "data.csv"
            db.write_text("a\n1\n")
            fake_q = _ScriptedQuestionary(
                prompts={
                    "api_key": "my-api-key",
                    "hq_url": "https://hq.example.org",
                    "keycloak_url": "https://auth.example.org",
                    "memory": "2g",
                },
                confirms=[
                    True,  # add a database
                    False,  # read-only access, no copy
                    False,  # don't add another database
                    True,  # add list of allowed_algorithms
                    False,  # don't add another algorithm image
                    False,  # no algorithm stores
                    True,  # limit algorithm containers
                    False,  # no encryption
                ],
                selects=[
                    "File database",
                    FILE_BASED_DATABASE_TYPES[0],
                    "INFO",
                ],
                texts=["default", str(db), "some-image"],
            )
            with patch("vantage6.cli.node.new.q", fake_q):
                config = node_configuration_questionaire(
                    data_dir="/data",
                    instance_name="iknl",
                    log_dir="/log",
                    runtime="docker",
                )
            self.assertFalse(fake_q.confirms or fake_q.selects or fake_q.texts)

        self.assertEqual(config["runtime"], "docker")
        node = config["node"]
        self.assertEqual(
            node["databases"]["fileBased"],
            [
                {
                    "name": "default",
                    "type": FILE_BASED_DATABASE_TYPES[0],
                    "path": str(db.resolve()),
                    "mount_mode": "ro",
                }
            ],
        )
        self.assertEqual(
            node["docker"]["algorithmContainers"], {"cpus": 4.0, "memory": "2g"}
        )
        for key in ("persistence", "networkPolicy", "resources", "algorithmPods"):
            self.assertNotIn(key, node)

    def _run_node_wizard(self, authenticate) -> dict:
        authenticate.side_effect = None
        fake_q = _ScriptedQuestionary(
            prompts={
                "api_key": "my-api-key",
                "hq_url": "https://hq.example.org/",
                "keycloak_url": "https://auth.example.org",
                "storageClass": "cephfs",
                "existingClaim": "hospital-data",
                "subPath": "exports/data.csv",
            },
            confirms=[
                False,  # no existing claim for the task files
                True,  # add a database
                False,  # don't add another database
                True,  # add list of allowed_algorithms
                False,  # don't add another algorithm image
                False,  # no algorithm stores
                False,  # may not create NetworkPolicies
                True,  # cluster requires resource requests and limits
                True,  # enable encryption (HQ cannot be asked, authentication is mocked)
            ],
            selects=[
                "ReadWriteMany",  # access mode of the task storage
                "File database",  # type of database to add
                FILE_BASED_DATABASE_TYPES[0],  # type of file database
                "DEBUG",  # level of logging
            ],
            texts=[
                "default",  # database label
                "some-image",  # allowed algorithm
            ],
        )
        with patch("vantage6.cli.node.new.q", fake_q):
            config = node_configuration_questionaire(
                data_dir="/data", instance_name="iknl", log_dir="/log"
            )
        self.assertFalse(fake_q.confirms or fake_q.selects or fake_q.texts)
        return config

    @patch("vantage6.cli.node.new.error")
    @patch("vantage6.cli.node.new._get_allowed_algorithm_stores")
    @patch("vantage6.cli.node.new._get_allowed_algorithms")
    @patch("vantage6.cli.node.new.q")
    def test_node_wizard_requires_algorithm_policy(
        self, q, get_algorithms, get_stores, error
    ):
        """Check the node wizard asks again until an algorithm policy is given."""
        q.confirm.return_value.unsafe_ask.side_effect = [
            False,  # don't add list of allowed_algorithms
            False,  # don't add algorithm stores
            True,  # add list of allowed_algorithms (second attempt)
            False,  # don't add algorithm stores (second attempt)
        ]
        get_algorithms.return_value = ["some-image"]

        policies = _get_algorithm_policies()

        self.assertEqual(
            policies, {NodePolicy.ALLOWED_ALGORITHMS.value: ["some-image"]}
        )
        error.assert_called_once()
        get_stores.assert_not_called()

    @patch("vantage6.cli.configuration_create.AppContext")
    @patch("vantage6.cli.configuration_create.q")
    @patch("vantage6.cli.hq.new.q")
    def test_hq_wizard(self, q, q_hq_common, app_context):
        app_context.instance_folders.return_value = {"log": "/log"}
        q.unsafe_prompt.side_effect = self.prompts
        q_hq_common.unsafe_prompt.side_effect = self.prompts
        q_hq_common.text.return_value.unsafe_ask.side_effect = [
            "postgresql://vantage6:vantage6@localhost:5432/vantage6",  # URI of database
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
            ["hq", "api_path"],
            ["hq", "keycloak"],
            ["hq", "logging"],
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
        node_m.return_value.save.side_effect = lambda path, **kwargs: path
        hq_m.return_value.save.side_effect = lambda path, **kwargs: path

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
