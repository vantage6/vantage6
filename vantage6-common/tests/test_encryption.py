import unittest

from cryptography.hazmat.primitives.serialization import load_pem_private_key

from vantage6.common.encryption import RSACryptor


class TestCreateNewRsaKeyPem(unittest.TestCase):
    def test_pem_without_file(self):
        pem = RSACryptor.create_new_rsa_key_pem()
        self.assertTrue(pem.startswith(b"-----BEGIN RSA PRIVATE KEY-----"))
        self.assertEqual(load_pem_private_key(pem, password=None).key_size, 4096)
