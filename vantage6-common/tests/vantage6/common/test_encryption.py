import stat
import tempfile
import unittest
from pathlib import Path

from vantage6.common.encryption import RSACryptor


class TestCreateNewRsaKey(unittest.TestCase):
    def test_key_file_is_owner_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private_key.pem"
            # a pre-existing world-readable file must be tightened as well
            path.write_text("old")
            path.chmod(0o644)

            RSACryptor.create_new_rsa_key(path)

            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertIn(b"PRIVATE KEY", path.read_bytes())
