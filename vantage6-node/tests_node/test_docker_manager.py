import unittest

from unittest.mock import MagicMock

from vantage6.common.globals import BASIC_PROCESSING_IMAGE, NodePolicy
from vantage6.node.docker.docker_manager import DockerManager

ALLOWED_IMAGE = "ghcr.io/example/allowed:latest"
OTHER_IMAGE = "ghcr.io/example/other:latest"
ALLOWED_IMAGE_PATTERN = r"^ghcr\.io/example/allowed:.*$"
ALLOWED_STORE = "https://store.example.org"
OTHER_STORE = "https://other.example.org"


class AlgorithmPolicyTest(unittest.TestCase):
    """Test policy evaluation in DockerManager.is_docker_image_allowed()."""

    def setUp(self):
        # We bypass DockerManager.__init__ because these checks do not need a
        # running Docker daemon. The mocked clients cover the few attributes used.
        self.manager = DockerManager.__new__(DockerManager)
        self.manager.log = MagicMock()
        self.manager.client = MagicMock()
        self.manager.docker = MagicMock()

    def is_allowed(
        self,
        policies: dict,
        image: str = ALLOWED_IMAGE,
        store_url: str | None = None,
    ) -> bool:
        # `policies` contains only the node configuration's `policies:` section,
        # not the complete node configuration. For example:
        # {"allowed_algorithms": [ALLOWED_IMAGE_PATTERN]}
        # The policy check expects the task's user and organization identifiers.
        # They are not relevant unless user or organization policies are configured.
        self.manager._policies = policies
        task_info = {
            "init_org": {"id": 1},
            "init_user": {"id": 1},
        }
        if store_url:
            # In normal operation the node retrieves the store URL from the server.
            task_info["algorithm_store"] = {"id": 1}
            self.manager.client.algorithm_store.get.return_value = {"url": store_url}
        return self.manager.is_docker_image_allowed(image, task_info)

    def test_no_algorithm_or_store_policy_rejects_all_images(self):
        # A missing `policies:` section is represented by an empty dictionary.
        self.assertFalse(self.is_allowed({}))

        # Explicitly configured but empty policy lists must behave the same way.
        self.assertFalse(
            self.is_allowed(
                {
                    NodePolicy.ALLOWED_ALGORITHMS: [],
                    NodePolicy.ALLOWED_ALGORITHM_STORES: [],
                }
            )
        )

    def test_algorithm_policy_can_be_used_on_its_own(self):
        # We do not require a store policy when an algorithm policy is configured.
        policies = {
            NodePolicy.ALLOWED_ALGORITHMS: [ALLOWED_IMAGE_PATTERN],
        }
        self.assertTrue(self.is_allowed(policies))
        self.assertFalse(self.is_allowed(policies, image=OTHER_IMAGE))

    def test_all_images_can_be_allowed_explicitly(self):
        # We retain allow-all behavior when the administrator explicitly requests it.
        policies = {
            NodePolicy.ALLOWED_ALGORITHMS: [".*"],
        }
        self.assertTrue(self.is_allowed(policies, image=OTHER_IMAGE))

    def test_store_policy_can_be_used_on_its_own(self):
        # We do not require an algorithm policy when a store policy is configured.
        policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES: [ALLOWED_STORE],
        }
        self.assertTrue(self.is_allowed(policies, store_url=ALLOWED_STORE))
        self.assertFalse(self.is_allowed(policies, store_url=OTHER_STORE))

    def test_both_policies_must_match_by_default(self):
        # With both policies configured, the default behavior requires both to match.
        policies = {
            NodePolicy.ALLOWED_ALGORITHMS: [ALLOWED_IMAGE_PATTERN],
            NodePolicy.ALLOWED_ALGORITHM_STORES: [ALLOWED_STORE],
        }
        self.assertTrue(self.is_allowed(policies, store_url=ALLOWED_STORE))
        self.assertFalse(
            self.is_allowed(policies, image=OTHER_IMAGE, store_url=ALLOWED_STORE)
        )
        self.assertFalse(self.is_allowed(policies, store_url=OTHER_STORE))

    def test_either_policy_can_match_when_enabled(self):
        # The opt-in setting changes the two-policy check from AND to OR.
        policies = {
            NodePolicy.ALLOWED_ALGORITHMS: [ALLOWED_IMAGE_PATTERN],
            NodePolicy.ALLOWED_ALGORITHM_STORES: [ALLOWED_STORE],
            "allow_either_whitelist_or_store": True,
        }
        self.assertTrue(
            self.is_allowed(policies, image=OTHER_IMAGE, store_url=ALLOWED_STORE)
        )
        self.assertTrue(self.is_allowed(policies, store_url=OTHER_STORE))
        self.assertFalse(
            self.is_allowed(policies, image=OTHER_IMAGE, store_url=OTHER_STORE)
        )

    def test_either_setting_does_not_bypass_a_single_policy(self):
        # A missing policy must not count as a match when OR behavior is enabled.
        algorithm_policies = {
            NodePolicy.ALLOWED_ALGORITHMS: [ALLOWED_IMAGE_PATTERN],
            "allow_either_whitelist_or_store": True,
        }
        self.assertTrue(self.is_allowed(algorithm_policies))
        self.assertFalse(self.is_allowed(algorithm_policies, image=OTHER_IMAGE))

        store_policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES: [ALLOWED_STORE],
            "allow_either_whitelist_or_store": True,
        }
        self.assertTrue(self.is_allowed(store_policies, store_url=ALLOWED_STORE))
        self.assertFalse(self.is_allowed(store_policies, store_url=OTHER_STORE))

    def test_basics_algorithm_is_rejected_without_an_allowed_image_policy(self):
        # The basics setting is an extra veto, not an independent allow-list.
        self.assertFalse(self.is_allowed({}, image=BASIC_PROCESSING_IMAGE))
