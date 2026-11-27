import unittest
from unittest.mock import MagicMock, patch

from vantage6.cli.hub.new import (
    _create_hub_config,
    _get_base_config,
    _validate_hostname,
)
from vantage6.cli.k8s_config import KubernetesConfig

module_path = "vantage6.cli.hub.new"


def _answer(value):
    """Return a questionary question mock that answers ``value``."""
    question = MagicMock()
    question.unsafe_ask.return_value = value
    return question


class HubNewTest(unittest.TestCase):
    def _get_base_config(self, single_host: bool, domain: str) -> dict:
        """Run the base configuration questions with the given routing choice."""

        def select(message, choices, default):
            if message.startswith("How will the hub services be reachable"):
                return _answer(choices[1] if single_host else choices[0])
            return _answer(default)

        with (
            patch(f"{module_path}.q") as q,
            patch(f"{module_path}.get_k8s_node_names", return_value=["node-1"]),
        ):
            q.select.side_effect = select
            q.text.side_effect = [_answer(domain), _answer("my-store")]
            q.confirm.return_value = _answer(True)
            return _get_base_config()

    def test_subdomains(self):
        """Each service gets its own subdomain and the store keeps /store."""
        base_config = self._get_base_config(single_host=False, domain="example.org")

        self.assertNotIn("single_host", base_config)
        self.assertEqual(base_config["hq_url"], "https://hq.example.org")
        self.assertEqual(base_config["auth_url"], "https://auth.example.org")
        self.assertEqual(base_config["ui_url"], "https://portal.example.org")
        self.assertEqual(base_config["store_url"], "https://store.example.org")
        self.assertEqual(base_config["store_api_path"], "/store")

        hub_config = _create_hub_config(
            "hub", base_config, KubernetesConfig(namespace="vantage6")
        )
        gateway = hub_config["hubGateway"]
        self.assertNotIn("host", gateway)
        self.assertEqual(
            gateway["hosts"],
            {
                "auth": "auth.example.org",
                "hq": "hq.example.org",
                "portal": "portal.example.org",
                "store": "store.example.org",
            },
        )

    def test_single_host(self):
        """All services share one hostname and the store API moves to /store-api."""
        base_config = self._get_base_config(single_host=True, domain="example.org")

        self.assertEqual(base_config["single_host"], "example.org")
        self.assertEqual(base_config["hq_url"], "https://example.org")
        self.assertEqual(base_config["auth_url"], "https://example.org/auth")
        self.assertEqual(base_config["ui_url"], "https://example.org")
        self.assertEqual(base_config["store_url"], "https://example.org")
        self.assertEqual(base_config["store_api_path"], "/store-api")

        hub_config = _create_hub_config(
            "hub", base_config, KubernetesConfig(namespace="vantage6")
        )
        gateway = hub_config["hubGateway"]
        self.assertEqual(gateway["host"], "example.org")
        self.assertEqual(gateway["hosts"], {})
        self.assertEqual(gateway["tls"]["existingSecrets"], {"hub": ""})
        self.assertEqual(
            hub_config["urls"]["external"]["auth"], "https://example.org/auth"
        )

    def test_validate_hostname(self):
        """Only a bare hostname is accepted."""
        self.assertTrue(_validate_hostname("example.org"))
        for invalid in [
            "",
            "https://example.org",
            "example.org/hub",
            "example.org:443",
        ]:
            self.assertIsInstance(_validate_hostname(invalid), str)
