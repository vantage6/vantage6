import unittest
from unittest.mock import MagicMock, patch

from vantage6.common.enum import AlgorithmStepType

from tests_store.base.unittest_base import TestResources
from vantage6.algorithm.store.default_roles import DefaultRole
from vantage6.algorithm.store.link_algorithms import (
    _parse_link_algorithms_config,
    link_algorithms_from_config,
)
from vantage6.algorithm.store.model.algorithm import Algorithm
from vantage6.algorithm.store.model.common.enums import Partitioning
from vantage6.algorithm.store.model.role import Role
from vantage6.algorithm.store.model.rule import Rule
from vantage6.algorithm.store.model.user import User


class TestLinkAlgorithms(TestResources):
    def test_all_disabled_does_not_seed(self):
        self.backend.ctx.config.pop("link_algorithms", None)
        n0 = len(Algorithm.get())
        link_algorithms_from_config(self.backend.ctx.config)
        self.assertEqual(len(Algorithm.get()), n0)

    def test_skips_without_root_user(self):
        self.backend.ctx.config.pop("root_user", None)
        self.backend.ctx.config["link_algorithms"] = {
            "list": [],
            "community": True,
            "basics": False,
            "demo": False,
        }
        link_algorithms_from_config(self.backend.ctx.config)

    def test_nested_store_link_algorithms_section(self):

        cfg = {
            "store": {
                "link_algorithms": {
                    "list": [],
                    "community": False,
                    "basics": True,
                    "demo": False,
                }
            }
        }
        parsed = _parse_link_algorithms_config(cfg)
        self.assertTrue(parsed["basics"])
        self.assertFalse(parsed["community"])

    @patch("vantage6.algorithm.store.link_algorithms.resolve_image_digest")
    @patch("vantage6.algorithm.store.link_algorithms.requests.get")
    def test_list_url_seeds_one_algorithm(self, mock_get, mock_digest):
        root_role = Role(name=DefaultRole.ROOT.value, rules=Rule.get())
        root_role.save()
        User(username="rootseed_link", roles=[root_role]).save()
        self.backend.ctx.config["root_user"] = {"username": "rootseed_link"}
        self.backend.ctx.config["dev"] = {"disable_review": True}

        mock_digest.return_value = ("ghcr.io/foo/bar:latest", "sha256:deadbeef")

        payload = {
            "name": "SeededFromList",
            "description": "d",
            "image": "ghcr.io/foo/bar:latest",
            "partitioning": Partitioning.HORIZONTAL.value,
            "vantage6_version": "5.0.0",
            "code_url": "https://github.com/o/r",
            "functions": [
                {
                    "name": "test_function",
                    "step_type": AlgorithmStepType.CENTRAL_COMPUTE.value,
                    "databases": [],
                    "arguments": [],
                    "ui_visualizations": [],
                }
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        n0 = len(Algorithm.get())
        self.backend.ctx.config["link_algorithms"] = {
            "list": ["https://example.invalid/meta.json"],
            "community": False,
            "basics": False,
            "demo": False,
        }
        link_algorithms_from_config(self.backend.ctx.config)

        self.assertEqual(len(Algorithm.get()), n0 + 1)
        created = Algorithm.get_by_image("ghcr.io/foo/bar:latest")
        self.assertTrue(any(a.name == "SeededFromList" for a in created))

    @patch("vantage6.algorithm.store.link_algorithms.resolve_image_digest")
    @patch("vantage6.algorithm.store.link_algorithms.requests.get")
    def test_idempotent_skip_existing_name(self, mock_get, mock_digest):
        root_role = Role(name=DefaultRole.ROOT.value, rules=Rule.get())
        root_role.save()
        User(username="rootseed_link2", roles=[root_role]).save()
        self.backend.ctx.config["root_user"] = {"username": "rootseed_link2"}
        self.backend.ctx.config["dev"] = {"disable_review": True}
        mock_digest.return_value = ("ghcr.io/foo/bar2:latest", "sha256:beefdead")

        payload = {
            "name": "DupAlgo",
            "description": "d",
            "image": "ghcr.io/foo/bar2:latest",
            "partitioning": Partitioning.HORIZONTAL.value,
            "vantage6_version": "5.0.0",
            "code_url": "https://github.com/o/r",
            "functions": [
                {
                    "name": "f",
                    "step_type": AlgorithmStepType.CENTRAL_COMPUTE.value,
                    "databases": [],
                    "arguments": [],
                    "ui_visualizations": [],
                }
            ],
        }
        mock_resp = MagicMock()
        mock_resp.json.return_value = payload
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        self.backend.ctx.config["link_algorithms"] = {
            "list": ["https://example.invalid/one.json"],
            "community": False,
            "basics": False,
            "demo": False,
        }
        link_algorithms_from_config(self.backend.ctx.config)
        n1 = len(Algorithm.get())
        link_algorithms_from_config(self.backend.ctx.config)
        self.assertEqual(len(Algorithm.get()), n1)


if __name__ == "__main__":
    unittest.main()
