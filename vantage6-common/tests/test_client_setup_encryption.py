import logging
from unittest import TestCase
from unittest.mock import MagicMock, patch

from vantage6.common.client.node_client import NodeClient
from vantage6.common.exceptions import PublicKeyMismatchError

MODULE = "vantage6.common.client.client_base"


class TestSetupEncryption(TestCase):
    """setup_encryption must never replace an organization's existing public key."""

    def setUp(self):
        self.client = object.__new__(NodeClient)
        self.client.log = logging.getLogger(__name__)
        self.client._access_token = "token"
        self.client.whoami = MagicMock(organization_id=3)

    def _setup(self, hq_public_key: str, key_matches: bool) -> MagicMock:
        cryptor = MagicMock(public_key_str="local-public-key")
        cryptor.verify_public_key.return_value = key_matches
        request = MagicMock(return_value={"public_key": hq_public_key})
        with (
            patch(f"{MODULE}.RSACryptor", return_value=cryptor),
            patch.object(NodeClient, "request", request),
        ):
            self.client.setup_encryption("/key.pem")
        return request

    def _uploads(self, request: MagicMock) -> list:
        return [c for c in request.call_args_list if c.kwargs.get("method") == "patch"]

    def test_uploads_when_organization_has_no_key(self):
        request = self._setup(hq_public_key="", key_matches=False)
        uploads = self._uploads(request)
        self.assertEqual(len(uploads), 1)
        self.assertEqual(uploads[0].kwargs["json"], {"public_key": "local-public-key"})

    def test_no_upload_when_key_matches(self):
        request = self._setup(hq_public_key="hq-key", key_matches=True)
        self.assertEqual(self._uploads(request), [])

    def test_raises_and_keeps_hq_key_on_mismatch(self):
        request = MagicMock(return_value={"public_key": "hq-key"})
        cryptor = MagicMock()
        cryptor.verify_public_key.return_value = False
        with (
            patch(f"{MODULE}.RSACryptor", return_value=cryptor),
            patch.object(NodeClient, "request", request),
            self.assertRaises(PublicKeyMismatchError),
        ):
            self.client.setup_encryption("/key.pem")
        self.assertEqual(self._uploads(request), [])
