import base64
import unittest
from unittest.mock import MagicMock, patch

from kubernetes.client.exceptions import ApiException

from vantage6.common.encryption import RSACryptor

from vantage6.cli.k8s_config import KubernetesConfig
from vantage6.cli.node.common.private_key import (
    PRIVATE_KEY_SECRET_KEY,
    delete_private_key_secret,
    private_key_secret_exists,
    private_key_secret_name,
    public_key_base64_from_pem,
    public_key_matches,
    read_private_key_secret,
    write_private_key_secret,
)

MODULE = "vantage6.cli.node.common.private_key"
PEM = RSACryptor.create_new_rsa_key_pem()
OTHER_PEM = RSACryptor.create_new_rsa_key_pem()
SECRET_NAME = "vantage6-iknl-user-node-private-key"


class TestPrivateKeySecret(unittest.TestCase):
    def setUp(self):
        self.ctx = MagicMock(helm_release_name="vantage6-iknl-user-node")
        self.k8s_config = KubernetesConfig(context="ctx", namespace="ns")
        self.core_api = MagicMock()
        patcher = patch(
            f"{MODULE}.get_core_api_with_ssl_handling", return_value=self.core_api
        )
        self.get_core_api = patcher.start()
        self.addCleanup(patcher.stop)

    def _secret_missing(self):
        self.core_api.read_namespaced_secret.side_effect = ApiException(status=404)

    def _secret_present(self, pem: bytes):
        self.core_api.read_namespaced_secret.side_effect = None
        self.core_api.read_namespaced_secret.return_value = MagicMock(
            data={PRIVATE_KEY_SECRET_KEY: base64.b64encode(pem).decode()}
        )

    def _created_pem(self) -> bytes:
        kwargs = self.core_api.create_namespaced_secret.call_args.kwargs
        self.assertEqual(kwargs["body"].metadata.name, SECRET_NAME)
        self.assertEqual(kwargs["namespace"], "ns")
        return kwargs["body"].string_data[PRIVATE_KEY_SECRET_KEY].encode()

    def test_secret_name_matches_chart(self):
        # charts/node mounts `{{ .Release.Name }}-private-key`
        self.assertEqual(private_key_secret_name(self.ctx), SECRET_NAME)

    def test_uses_selected_context(self):
        self._secret_missing()
        read_private_key_secret(self.ctx, self.k8s_config)
        self.get_core_api.assert_called_with(context="ctx")

    def test_read_secret(self):
        self._secret_missing()
        self.assertIsNone(read_private_key_secret(self.ctx, self.k8s_config))
        self._secret_present(PEM)
        self.assertEqual(read_private_key_secret(self.ctx, self.k8s_config), PEM)

    def test_write_new_secret(self):
        self._secret_missing()
        write_private_key_secret(self.ctx, self.k8s_config, PEM)
        self.assertEqual(self._created_pem(), PEM)
        self.core_api.delete_namespaced_secret.assert_not_called()

    def test_write_replaces_existing_secret(self):
        self._secret_present(OTHER_PEM)
        write_private_key_secret(self.ctx, self.k8s_config, PEM)
        self.core_api.delete_namespaced_secret.assert_called_once_with(
            name=SECRET_NAME, namespace="ns"
        )
        self.assertEqual(self._created_pem(), PEM)

    def test_secret_exists(self):
        self._secret_missing()
        self.assertFalse(private_key_secret_exists(self.ctx, self.k8s_config))
        self._secret_present(PEM)
        self.assertTrue(private_key_secret_exists(self.ctx, self.k8s_config))

    def test_delete_secret(self):
        self.assertTrue(delete_private_key_secret(self.ctx, self.k8s_config))
        self.core_api.delete_namespaced_secret.side_effect = ApiException(status=404)
        self.assertFalse(delete_private_key_secret(self.ctx, self.k8s_config))
        self.core_api.delete_namespaced_secret.side_effect = ApiException(status=500)
        with self.assertRaises(ApiException):
            delete_private_key_secret(self.ctx, self.k8s_config)


class TestPublicKeyMatches(unittest.TestCase):
    def test_matches_own_public_key(self):
        self.assertTrue(public_key_matches(PEM, public_key_base64_from_pem(PEM)))

    def test_does_not_match_other_public_key(self):
        self.assertFalse(public_key_matches(PEM, public_key_base64_from_pem(OTHER_PEM)))
