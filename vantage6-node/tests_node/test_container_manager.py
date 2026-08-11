import logging
import os
import unittest
from unittest.mock import MagicMock, patch

from vantage6.common.globals import NodePolicy

from vantage6.node.k8s.container_manager import ContainerManager


def _get_null_logger(name="null_logger_container_manager"):
    logger = logging.getLogger(name)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


class TestIsImageAllowed(unittest.TestCase):
    """
    Tests for ContainerManager.is_image_allowed().

    ContainerManager.__init__ talks to the Kubernetes API, so these tests bypass it
    (via __new__) and set up only the attributes is_image_allowed() actually reads:
    `_policies`, `client` and `log`. This keeps `_is_regex_pattern` (a real
    staticmethod on the class) working, unlike a fully mocked `self` would.
    """

    def setUp(self):
        self.manager = ContainerManager.__new__(ContainerManager)
        self.manager.log = _get_null_logger()
        self.manager.client = MagicMock()
        self.manager._policies = {}

    @staticmethod
    def _task_info(store_id: int | None = None) -> dict:
        task_info = {"init_org": {"id": 1}, "init_user": {"id": 1}}
        if store_id is not None:
            task_info["algorithm_store"] = {"id": store_id}
        return task_info

    def test_allowed_algorithms_exact_match(self):
        """Baseline regression check for the (unchanged) allowed_algorithms policy."""
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHMS.value: ["some/image:tag"]
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info())
        )
        self.assertFalse(
            self.manager.is_image_allowed("some/other-image:tag", self._task_info())
        )

    def test_allowed_algorithm_stores_verified(self):
        """
        The store URL is whitelisted and the store itself confirms the image is a
        registered, approved algorithm there - the image is allowed.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )
        self.manager.client.algorithm_store.get_algorithm.assert_called_once_with(
            "some/image:tag"
        )

    def test_allowed_algorithm_stores_not_confirmed_by_store(self):
        """
        The store URL is whitelisted, but the store does not confirm the image is
        registered/approved there (e.g. it genuinely isn't, the store hasn't been
        upgraded to support node requests, or it could not be reached) - the image
        is denied. This is the fix for GHSA-j43v-wwjr-9grj: previously the store URL
        match alone was enough.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = None

        self.assertFalse(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )

    def test_allowed_algorithm_stores_url_not_whitelisted(self):
        """
        The store's URL isn't on the whitelist at all - the image is denied without
        even asking the store to verify the image (no wasted network call).
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://trusted.example"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://untrusted.example",
            "api_path": "/api",
        }

        self.assertFalse(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )
        self.manager.client.algorithm_store.get_algorithm.assert_not_called()

    def test_allowed_algorithm_stores_localhost_translated_in_k8s(self):
        """
        A store registered under a `localhost` URL (e.g. running on the same local
        dev machine as the node) is translated to an address reachable from inside
        the node's pod before the live verification call, when V6_K8S_NODE_NAME
        indicates a local k8s dev deployment.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["http://localhost:7601"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "http://localhost:7601",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        with patch.dict(os.environ, {"V6_K8S_NODE_NAME": "docker-desktop"}):
            self.assertTrue(
                self.manager.is_image_allowed(
                    "some/image:tag", self._task_info(store_id=1)
                )
            )

        self.assertEqual(
            self.manager.client.algorithm_store.url,
            "http://host.docker.internal:7601/api",
        )

    def test_allowed_algorithm_stores_localhost_unchanged_without_k8s_node(self):
        """
        Without V6_K8S_NODE_NAME set (the default outside local dev deployments), a
        `localhost` store URL is used as-is - a real deployment never has the node
        and the store on the same machine, so there is nothing to translate.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["http://localhost:7601"]
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "http://localhost:7601",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("V6_K8S_NODE_NAME", None)
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))

        self.assertEqual(
            self.manager.client.algorithm_store.url, "http://localhost:7601/api"
        )

    def test_allow_either_whitelist_or_store(self):
        """
        Baseline regression check: with allow_either_whitelist_or_store, an image
        that fails the allowed_algorithms whitelist but is confirmed by the
        (whitelisted) store is still allowed.
        """
        self.manager._policies = {
            NodePolicy.ALLOWED_ALGORITHMS.value: ["some/other-image:tag"],
            NodePolicy.ALLOWED_ALGORITHM_STORES.value: ["https://store.example"],
            "allow_either_whitelist_or_store": True,
        }
        self.manager.client.algorithm_store.get.return_value = {
            "url": "https://store.example",
            "api_path": "/api",
        }
        self.manager.client.algorithm_store.get_algorithm.return_value = {
            "image": "some/image:tag",
            "digest": "abc123",
        }

        self.assertTrue(
            self.manager.is_image_allowed("some/image:tag", self._task_info(store_id=1))
        )


if __name__ == "__main__":
    unittest.main()
